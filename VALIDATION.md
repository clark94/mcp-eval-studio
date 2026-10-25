# Validation de la livraison

- Tests pytest : 2 tests réussis (calcul physique, authentification, validation, origine interdite, erreur outil et ressource absente).
- Test réel sur serveur Uvicorn : création d'une évaluation, exécution asynchrone, appels MCP HTTP, quatre scénarios réussis sur quatre, lecture du rapport et export JSON.
- Environnement de vérification : Python 3.12 ; image Docker ciblée Python 3.11.
- Non exécutés : build Docker, émission de certificat HTTPS, déploiement public, appels payants LLM, export vers une instance MLflow et intégration Amesim.
- L'interface a été servie avec succès, mais n'a pas fait l'objet d'une vérification visuelle automatisée en navigateur.
- Un avertissement de dépréciation AnyIO/Starlette apparaît pendant les tests, sans échec.
