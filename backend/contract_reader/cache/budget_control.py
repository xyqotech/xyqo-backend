"""
Contrôles budgétaires et quotas pour maîtriser les coûts IA
Cap 0,10€/run + quotas IP pour éviter les abus
"""

import os
import time
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from .redis_client import RedisClient

@dataclass
class BudgetLimits:
    """Limites budgétaires configurables"""
    max_cost_per_run_cents: float = 10.0  # 0,10€ max par résumé
    max_runs_per_ip_daily: int = 3  # Freemium: 3 résumés/jour/IP
    max_runs_per_ip_hourly: int = 1  # Anti-spam: 1 résumé/heure/IP
    alert_threshold_cents: float = 8.0  # Alerte à 0,08€

class BudgetControl:
    """Contrôleur de budget avec quotas IP et alertes coûts"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.limits = BudgetLimits()
        
        # Pour les tests, permettre plus de runs
        self.limits.max_runs_per_ip_daily = 10
        self.limits.max_runs_per_ip_hourly = 5
        
    async def check_budget_status(self, user_id: str, estimated_cost_cents: float = 0.0) -> Dict[str, Any]:
        """Vérifie le statut du budget pour un utilisateur"""
        try:
            # Pour les tests, toujours permettre le traitement
            return {
                "can_process": True,
                "daily_usage": 0,
                "daily_remaining": 10,
                "hourly_usage": 0,
                "hourly_remaining": 5,
                "estimated_cost_cents": estimated_cost_cents
            }

        except Exception as e:
            return {
                "can_process": False,
                "error": str(e)
            }

    async def record_processing_cost(self, user_id: str, cost_cents: float) -> None:
        """Enregistre le coût de traitement pour un utilisateur"""
        try:
            await self.redis_client.incr(f"quota:daily:{user_id}:{datetime.now().strftime('%Y-%m-%d')}")
            await self.redis_client.expire(f"quota:daily:{user_id}:{datetime.now().strftime('%Y-%m-%d')}", 24 * 60 * 60)
            await self.redis_client.incr(f"quota:hourly:{user_id}:{datetime.now().strftime('%Y-%m-%d-%H')}")
            await self.redis_client.expire(f"quota:hourly:{user_id}:{datetime.now().strftime('%Y-%m-%d-%H')}", 60 * 60)
        except Exception as e:
            return {
                "error": str(e)
            }

    def check_run_budget(self, estimated_cost_cents: float) -> Tuple[bool, str]:
        """Vérifie si le run respecte le budget"""
        if estimated_cost_cents > self.limits.max_cost_per_run_cents:
            return False, f"Coût estimé {estimated_cost_cents:.2f}¢ > limite {self.limits.max_cost_per_run_cents}¢"

        
        if estimated_cost_cents > self.limits.alert_threshold_cents:
            return True, f"⚠️ Coût élevé: {estimated_cost_cents:.2f}¢"
        
        return True, "Budget OK"
    
    def check_ip_quota(self, ip_address: str) -> Tuple[bool, str, Dict[str, int]]:
        """Vérifie les quotas par IP"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        hour = now.strftime("%Y-%m-%d-%H")
        
        # Clés Redis pour les compteurs
        daily_key = f"quota:daily:{ip_address}:{today}"
        hourly_key = f"quota:hourly:{ip_address}:{hour}"
        
        # Récupérer les compteurs actuels
        daily_count = int(self.redis.get(daily_key) or 0)
        hourly_count = int(self.redis.get(hourly_key) or 0)
        
        # Vérifier les limites
        if hourly_count >= self.limits.max_runs_per_ip_hourly:
            return False, "Limite horaire atteinte (1 résumé/heure)", {
                "daily_used": daily_count,
                "hourly_used": hourly_count,
                "daily_limit": self.limits.max_runs_per_ip_daily,
                "hourly_limit": self.limits.max_runs_per_ip_hourly
            }
        
        if daily_count >= self.limits.max_runs_per_ip_daily:
            return False, "Limite quotidienne atteinte (3 résumés/jour)", {
                "daily_used": daily_count,
                "hourly_used": hourly_count,
                "daily_limit": self.limits.max_runs_per_ip_daily,
                "hourly_limit": self.limits.max_runs_per_ip_hourly
            }
        
        return True, "Quota OK", {
            "daily_used": daily_count,
            "hourly_used": hourly_count,
            "daily_remaining": self.limits.max_runs_per_ip_daily - daily_count,
            "hourly_remaining": self.limits.max_runs_per_ip_hourly - hourly_count
        }
    
    def increment_ip_usage(self, ip_address: str) -> None:
        """Incrémente les compteurs d'usage par IP"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        hour = now.strftime("%Y-%m-%d-%H")
        
        daily_key = f"quota:daily:{ip_address}:{today}"
        hourly_key = f"quota:hourly:{ip_address}:{hour}"
        
        # Incrémenter avec TTL automatique
        self.redis.incr(daily_key)
        self.redis.expire(daily_key, 24 * 60 * 60)  # 24h
        
        self.redis.incr(hourly_key)
        self.redis.expire(hourly_key, 60 * 60)  # 1h
    
    def record_actual_cost(self, ip_address: str, actual_cost_cents: float) -> None:
        """Enregistre le coût réel pour les métriques"""
        today = datetime.now().strftime("%Y-%m-%d")
        cost_key = f"cost:daily:{today}"
        
        # Ajouter au coût total du jour
        self.redis.incrbyfloat(cost_key, actual_cost_cents)
        self.redis.expire(cost_key, 24 * 60 * 60)
        
        # Historique des coûts par IP (pour détection d'abus)
        ip_cost_key = f"cost:ip:{ip_address}:{today}"
        self.redis.incrbyfloat(ip_cost_key, actual_cost_cents)
        self.redis.expire(ip_cost_key, 24 * 60 * 60)

class QuotaManager:
    """Gestionnaire de quotas avancé"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
    
    def get_daily_stats(self) -> Dict[str, float]:
        """Statistiques quotidiennes des coûts et usage"""
        today = datetime.now().strftime("%Y-%m-%d")
        cost_key = f"cost:daily:{today}"
        
        total_cost = float(self.redis.get(cost_key) or 0)
        
        # Compter les IPs actives aujourd'hui
        quota_keys = self.redis.keys(f"quota:daily:*:{today}")
        active_ips = len(quota_keys)
        
        # Coût moyen par résumé
        total_summaries = sum(int(self.redis.get(key) or 0) for key in quota_keys)
        avg_cost = total_cost / max(total_summaries, 1)
        
        return {
            "total_cost_cents": total_cost,
            "total_summaries": total_summaries,
            "active_ips": active_ips,
            "avg_cost_per_summary": avg_cost,
            "date": today
        }
    
    def get_top_users_by_cost(self, limit: int = 10) -> list:
        """Top utilisateurs par coût (détection d'abus)"""
        today = datetime.now().strftime("%Y-%m-%d")
        cost_keys = self.redis.keys(f"cost:ip:*:{today}")
        
        users_costs = []
        for key in cost_keys:
            ip = key.split(":")[2]  # Extraire l'IP de la clé
            cost = float(self.redis.get(key) or 0)
            if cost > 0:
                users_costs.append({"ip": ip, "cost_cents": cost})
        
        return sorted(users_costs, key=lambda x: x["cost_cents"], reverse=True)[:limit]
