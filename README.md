# Tracker Stages · France, Suisse, Singapour

Surveille en continu les offres de stage (off-cycle, césure, et summer en Suisse et à Singapour) en M&A / IBD,
Private Equity, Venture Capital, Sales & Trading, Asset Management et Commodities, à **Paris et en Île-de-France**,
en **Suisse** (Genève surtout, aussi Zurich, Lausanne, Zoug, Lugano…) et à **Singapour**. Chaque nouvelle offre
déclenche une **notification** qui indique le lieu (« 📍 Genève, Suisse ») et ouvre la page de candidature.

Version en ligne : GitHub Actions lance `python tracker.py --cloud` toutes les 10 minutes, les notifications
passent par ntfy et le tableau de bord est publié sur GitHub Pages, avec un onglet par zone.

## Installation (Windows, 5 minutes, une seule fois)

1. Installe Python si besoin : https://www.python.org/downloads/ (coche **Add python.exe to PATH**).
2. Dézippe le dossier où tu veux (par exemple dans Documents).
3. Double-clique sur **1_Installer.bat**. Il installe les modules, affiche une notification de test,
   puis lance un diagnostic qui teste chaque source depuis ton PC.
4. Double-clique sur **2_Lancer_le_tracker.bat**. Laisse la fenêtre ouverte (réduite).
5. Optionnel : **3_Demarrage_automatique.bat** pour qu'il se lance à chaque démarrage du PC.

Sur Mac : double-clique sur `Lancer_sur_Mac.command` (et `brew install terminal-notifier` pour des
notifications cliquables).

## Ce que tu obtiens

* **Une notification par nouvelle offre** (entreprise, catégorie, intitulé). Clic ou bouton « Postuler »
  → page de candidature. Au-delà de 5 offres d'un coup, une seule notification groupée ouvre le tableau de bord.
* **Le tableau de bord** `data/tableau_de_bord.html` (s'ouvre au lancement, se recharge seul) :
  toutes les offres triées par date de détection, filtres par catégorie, recherche, « Nouvelles 24 h »,
  case **Postulé** pour suivre tes candidatures (mémorisée dans ton navigateur).
* **Lien direct carrière** : pour les offres LinkedIn, le tracker récupère le lien du site carrière de
  l'entreprise quand l'offre en a un (bouton « Postuler (site carrière) »). Sinon, candidature via LinkedIn.

Au tout premier lancement, les offres déjà en ligne sont ajoutées au tableau **sans notification**
(une seule notification « Tracker prêt »). Ensuite, chaque nouvelle offre est notifiée une fois, une seule.

## Sources

| Source | Couverture |
|---|---|
| LinkedIn (offres publiques) | Quasi toutes les banques (BNP, SG, CACIB, Natixis, GS, MS, JPM…), boutiques M&A, fonds |
| Welcome to the Jungle | Fonds VC/PE et boutiques françaises qui ne publient pas sur LinkedIn |
| Sites carrières (Workday, Oracle, SmartRecruiters, pages HTML) | Une cinquantaine de banques, fonds et négociants (Lazard, Rothschild, Goldman Sachs, Julius Baer, UBP, Vitol, Trafigura, Gunvor, DBS, Temasek, GIC…) |
| MyCareersFuture | Portail public de l'emploi à Singapour (stages « Internship/Attachment ») |

Non utilisés car leurs conditions d'utilisation ou leur robots.txt l'interdisent : jobup.ch, jobs.ch,
eFinancialCareers, JobTeaser. Ces offres restent en grande partie visibles via LinkedIn et les sites carrières.

Recherche toutes les ~10 minutes, avec des pauses aléatoires pour ne pas être bloqué.
Si un site limite les requêtes, le tracker se met en pause sur ce site seulement et reprend tout seul.
L'état de chaque source est affiché en bas du tableau de bord.

## Filtre appliqué

Une offre est retenue seulement si **les trois conditions** sont réunies :

1. **Stage** : stage, stagiaire, intern, off-cycle, césure, summer… (vérifié dans la description et le
   type de contrat quand l'intitulé ne le dit pas). Exclus : alternance, apprentissage, VIE, CDI, CDD.
2. **Zone** : Paris et Île-de-France, Suisse ou Singapour (les summer internships sont gardés partout ;
   `include_summer: false` ne les retire qu'en France).
3. **Métier** : M&A / IBD (M&A, ECM, DCM, LevFin, corporate finance…), Private Equity, Venture Capital,
   Sales & Trading / Sales marchés, Asset Management (gestion, trading, investment research), Commodities
   (trading, analyse, opérations liées au négoce). Exclus : structuring, quant, strats, risk, audit,
   transaction services, IT/data, compliance, juridique, gestion de fortune, et les « sales » commerciaux hors marchés.

## Personnaliser (`config.json`, créé au premier lancement)

* `interval_minutes` : fréquence (10 par défaut, ne descends pas sous 5).
* `linkedin.queries` / `wttj.queries` : mots-clés de recherche.
* `workday.tenants` : ajouter une banque sur Workday (host, tenant, site visibles dans l'URL de son site carrière,
  par exemple `https://barclays.wd3.myworkdayjobs.com/External_Career_Site_Barclays` →
  host `barclays.wd3.myworkdayjobs.com`, tenant `barclays`, site `External_Career_Site_Barclays`).
* `filters.extra_include` : mots qui suffisent à retenir une offre (ex. `"transaction services"`).
* `filters.extra_exclude` : mots qui excluent une offre.
* `filters.include_summer` : `false` pour ignorer les summer internships.

Redémarre le tracker après une modification.

## Commandes utiles

```
python tracker.py --check       diagnostic des sources
python tracker.py --test-notif  notification de test
python tracker.py --reset       efface la mémoire (tout sera reconsidéré comme nouveau)
```

Le PC doit être allumé et le tracker lancé pour recevoir les notifications. Journal : `data/tracker.log`.
