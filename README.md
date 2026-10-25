# MCP Eval Studio

Plateforme pédagogique d'évaluation de workflows MCP et de modèles de langage. Interface française, API FastAPI, serveur MCP de démonstration, historique SQLite, file persistante et export JSON. Aucun lien officiel avec Siemens ; aucun accès réel à Amesim.

## Démarrage avec Docker — Windows, Linux ou macOS

1. Installer Docker avec Docker Compose.
2. Extraire ce dossier et ouvrir un terminal dedans.
3. Copier `.env.example` vers `.env` (`Copy-Item .env.example .env` dans PowerShell, `cp .env.example .env` dans bash).
4. Générer un jeton avec `python -c "import secrets; print(secrets.token_urlsafe(36))"`. Remplacer la valeur ADMIN_TOKEN dans `.env` par ce jeton. Ne jamais le publier sur GitHub.
5. Exécuter `docker compose up --build -d`.
6. Ouvrir http://localhost:8000 et saisir le jeton.
7. Lancer une évaluation **Référence déterministe**. Les quatre scénarios doivent réussir. Ce mode vérifie le moteur, le transport et le simulateur ; il ne mesure pas l'intelligence d'un agent.

Arrêter : `docker compose down`. Les résultats restent dans le volume `studio_data`. Ne pas ajouter `-v` si vous souhaitez les conserver.

## Agent LLM réel (facultatif et potentiellement payant)

Configurer LLM_API_KEY, LLM_MODEL (identifiant fourni par votre fournisseur) et LLM_BASE_URL, puis `docker compose up -d --force-recreate studio`. Utiliser un endpoint compatible Chat Completions avec tool calling. La clé reste sur le serveur. L'agent sélectionne un outil, fournit les paramètres, puis génère une explication. Les évaluations stockent ses paramètres, sorties et tokens signalés par le fournisseur. Le juge LLM est un appel séparé, indicatif ; son coût et ses tokens ne sont pas inclus dans les usages affichés. Aucune estimation monétaire n'est présentée. Limiter le budget chez le fournisseur.

## Déploiement HTTPS sur un serveur

Serveur avec Docker et stockage persistant, domaine pointant vers son IP, ports entrants 80/443 autorisés. Copier le projet et son `.env` par un canal sécurisé. Configurer DOMAIN avec votre domaine réel (sans https://) et ALLOWED_ORIGINS avec son origine complète, par exemple `https://eval.votredomaine.fr`. Lancer :

```
docker compose --profile https up --build -d
```

Caddy sert le site et provisionne HTTPS si le DNS et les ports sont corrects. L'API reste liée à 127.0.0.1 sur le serveur. Ne pas exposer le port 8000 publiquement. Configuration pour une **démonstration privée mono-équipe** : un seul jeton partagé, pas de gestion de comptes individuels, de rôles ou de tenants. Pour une plateforme d'entreprise : ajouter OIDC/SSO, RBAC, PostgreSQL, worker externe, politiques de rétention, journal d'audit et supervision. Aucune certification ni audit de sécurité n'est revendiqué.

## Architecture et limites

- Un processus Uvicorn, un worker séquentiel en thread, SQLite avec file persistante. Ne pas lancer plusieurs workers/instances : cela exigerait un mécanisme de claim distribué.
- Trois exécutions simultanément en attente/en cours au maximum ; appels LLM bornés par timeout. Les historiques sont affichés par lots de 100, sans suppression automatique.
- Une évaluation en cours lors d'un arrêt est marquée `interrupted` au redémarrage ; les évaluations en attente sont reprises. Relancer manuellement les évaluations interrompues.
- API et interface sur la même origine ; authentification Bearer sur toutes les routes de données et MCP. Garder le jeton privé, accès HTTPS obligatoire en ligne. Pas de données confidentielles dans une démo publique.
- Le transport MCP implémente un sous-ensemble JSON-RPC Streamable HTTP **2025-11-25**, stateless JSON : initialize, ping, tools/list, tools/call, notification initialized. Pas un SDK complet ni une certification MCP. Le runner est volontairement limité à ce serveur ; ne pas lui donner directement une URL Amesim arbitraire.
- Scénarios fixes dans `app/engine.py`. Modèle du premier ordre : y(t)=gain*(1-exp(-t/tau)). Vérification des paramètres ET résultat indépendant avec tolérance. Le cas tau=0 doit produire une erreur contrôlée.
- Une seule étape d'outil par scénario. L'extension aux workflows multi-étapes nécessite de nouveaux scénarios et une boucle d'agent bornée.
- Aucun coût LLM chiffré, aucun connecteur Amesim, Go, Streamlit, MLflow ou PostgreSQL intégré au runtime principal. L'interface HTML évite de multiplier les services pour ce premier prototype.

## Export MLflow (optionnel)

Un script permet d'importer les rapports JSON dans votre instance MLflow existante. Installer `pip install -r requirements-mlflow.txt`, configurer MLFLOW_TRACKING_URI et lancer `python scripts/export_mlflow.py evaluation.json`. Les artefacts conservent les résultats complets. Les métriques contiennent le taux de réussite et la latence moyenne. Ne pas exposer MLflow sans authentification.

## Tests et CI

```
pip install -r requirements.txt
python -m pytest -q
```

GitHub Actions lance les tests à chaque push/PR. Les tests de base ne nécessitent pas de fournisseur LLM. Les différences entre fournisseurs doivent être mesurées séparément sur les mêmes scénarios. Le fichier VALIDATION.md décrit les vérifications réalisées sur cette livraison.

## Raccordement futur à Siemens Amesim

Obtenir licences, API, serveur MCP Nexus, autorisations et jeux de résultats de référence. Construire un adaptateur client avec le SDK MCP compatible avec leur version et leurs schémas. Prévoir un worker dans leur environnement privé si Amesim n'est pas accessible depuis le cloud. Définir unités, tolérances physiques et critères de réussite avec les experts. Ce simulateur ne valide aucune simulation Amesim.

## Sauvegardes

Avant sauvegarde, arrêter `studio`, sauvegarder le volume `studio_data` avec votre outil de sauvegarde Docker, puis redémarrer. Conserver `.env` dans un coffre sécurisé distinct. Tester la restauration sur un serveur isolé. Sauvegarder aussi les volumes Caddy pour conserver les certificats.

## Références

- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://mlflow.org/docs/latest/ml/tracking/tracking-api/

Ces dépendances sont épinglées pour la reproductibilité de ce prototype, pas présentées comme les dernières versions. Les mettre à jour après tests avant exploitation durable.
