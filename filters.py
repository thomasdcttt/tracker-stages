"""Filtrage des offres : stage/off-cycle + zone (Paris, Suisse, Singapour) + IBD (M&A, PE, VC), S&T, AM, Commodities.

Tout se joue sur du texte normalisé (minuscules, sans accents, ponctuation -> espaces).
Les listes sont volontairement explicites pour pouvoir être ajustées dans config.json.
"""
import re
import unicodedata

# À incrémenter à chaque changement de règles : les offres déjà écartées sont alors réexaminées.
FILTER_VERSION = 11


def normalize(text):
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    # Formes de M&A avant de supprimer la ponctuation
    t = re.sub(r"\bm\s*&\s*a\b", " mna ", t)
    t = re.sub(r"\bm\s*and\s*a\b", " mna ", t)
    t = re.sub(r"\bm\s*/\s*a\b", " mna ", t)
    t = re.sub(r"\bs\s*&\s*t\b", " sales trading ", t)
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " " + re.sub(r"\s+", " ", t).strip() + " "


def _rx(words):
    """Compile une liste de motifs en regex à frontières de mots (sur texte normalisé)."""
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(words) + r")(?![a-z0-9])")


# ---------- Type de contrat ----------
INTERN_TITLE = _rx([
    r"stages?", r"stagiaires?", r"interns?", r"internships?", r"off ?cycle", r"offcycle",
    r"cesure", r"gap year", r"summer analysts?", r"summer internship", r"spring internship",
    r"winter internship", r"autumn internship", r"fall internship",
    # "Placement" (Citi, Barclays...) = stage ; "trainee" seul ne suffit pas (souvent un CDI junior)
    r"placement analysts?", r"placement (?:year|programme|program|student)", r"industrial placement",
    # Allemand (Suisse alémanique)
    r"praktikums?", r"praktika", r"praktikant(?:in|innen|en)?",
    # v7 : Hochschulpraktikum, Jahrespraktikum, Hochschulpraktikant/-in...
    r"\w+praktik(?:um|ums|a|ant\w*)",
    # v7 : "Summer Associate" (Goldman Sachs, Capital Group...) = stage d'été
    r"summer associates?",
    # v10 : "Summer Financial Analyst" (Houlihan Lokey), "Year in Industry" (Legal & General) = stage
    r"summer (?:\w+ ){1,2}analysts?", r"year in industry",
])
SUMMER_TITLE = _rx([r"summer"])
# Contrats explicitement exclus
CONTRACT_EXCLUDE = _rx([
    r"alternance", r"alternant", r"alternante", r"apprenti", r"apprentie", r"apprentissage",
    r"apprenticeship", r"v i e", r"volontariat international", r"cdi", r"cdd",
    r"contrat pro", r"contrat de professionnalisation", r"work ?study", r"phd", r"doctorat",
    # Allemand : étudiant salarié, apprentissage (Lehre / Lernende)
    r"werkstudent\w*", r"lehrstelle\w*", r"lernende[nr]?", r"lehrling\w*",
    # v7 : "Working Student" (J.P. Morgan, Swiss Life AM) = Werkstudent, pas un stage
    r"working students?",
    # v10 : "Full Time Analyst ... (Applicable for 2026 Citi Summer interns only)" : CDI réservé aux anciens stagiaires
    r"full ?time (?:analysts?|associates?)",
    # v10 : programmes de découverte d'une semaine ou d'un jour (hors périmètre : ni stage ni poste)
    r"spring weeks?", r"spring insights?", r"insight (?:weeks?|days?|programmes?|programs?|events?)",
    r"(?:women s |diversity )?immersion (?:programmes?|programs?|days?|weeks?)", r"discovery (?:days?|weeks?)",
    r"open days?", r"virtual experience",
])
# Titres de postes confirmés ou de programmes graduate : jamais un stage si le titre ne dit pas "stage"/"intern"
NOT_INTERN_TITLE = _rx([
    r"senior", r"sr", r"vp", r"avp", r"vice president", r"directors?", r"directeur\w*", r"directrice\w*",
    r"head", r"managing", r"managers?", r"associates?",
    r"lead", r"principal", r"partner", r"experienced", r"experimente\w*", r"confirme\w*", r"expert\w*",
    r"\d+ ?(?:ans|years|yrs|year)", r"graduates?", r"graduate program\w*", r"new grads?", r"fresh grad\w*",
    r"full ?time", r"temps plein", r"permanent", r"contract", r"contractor", r"freelance", r"officer",
    r"specialist", r"specialiste", r"executive", r"responsable", r"chief", r"team head", r"heads?",
])
# "Assistant(e) ..." : intitulé usuel des stages en France, c'est le type de contrat qui tranche
ASSISTANT_TITLE = _rx([r"assistante?s?", r"assistant e"])
# "(with commodities/bank internship or work experience)" : l'expérience demandée n'est pas le contrat
INTERN_EXPERIENCE = re.compile(
    r"(?<![a-z0-9])(?:\w+ ){0,3}internships? (?:and |or )?(?:work |relevant )?(?:experiences?|exposure|background)(?![a-z0-9])")
# Faux positifs anglais/français de "stage" dans les descriptions (early stage, etc.)
STAGE_FALSE = re.compile(
    r"(?<![a-z0-9])(?:early|growth|late|later|seed|any|every|all|this|that|next|first|"
    r"second|final|each|multi|mid|pre|post|clinical|development|developpement|commercial|"
    r"advanced|initial|current|same|various|different|critical|key|new|young)\s+stages?(?![a-z0-9])"
)
INTERN_DESC = re.compile(
    r"(?<![a-z0-9])(?:internships?|off ?cycle|cesure|gap year|"
    r"praktikums?|praktikant(?:in|en)?|convention de stage|stage de \d+|stage d une duree|stage a pourvoir|"
    r"duree du stage|offre de stage|stage de fin d etudes|stage (?:de )?(?:\d+|six|quatre|cinq) mois)(?![a-z0-9])"
)

# ---------- Lieu ----------
PARIS_LOC = _rx([
    r"paris", r"ile de france", r"idf", r"la defense", r"puteaux", r"courbevoie", r"neuilly",
    r"neuilly sur seine", r"levallois", r"levallois perret", r"boulogne", r"boulogne billancourt",
    r"issy les moulineaux", r"saint denis", r"montrouge", r"nanterre", r"clichy", r"saint cloud",
    r"rueil malmaison", r"suresnes", r"saint ouen", r"vincennes", r"charenton", r"ivry sur seine",
    r"montreuil", r"pantin", r"aubervilliers", r"saint mande", r"fontenay sous bois", r"nogent sur marne",
    r"malakoff", r"vanves", r"clamart", r"meudon", r"sevres", r"chatillon", r"bagneux", r"arcueil",
    r"gentilly", r"kremlin bicetre", r"colombes", r"bois colombes", r"la garenne colombes",
    r"asnieres(?: sur seine)?", r"gennevilliers", r"bobigny", r"noisy le grand", r"marne la vallee",
    r"versailles", r"saint germain en laye", r"guyancourt", r"saint quentin en yvelines", r"velizy\w*",
    r"massy", r"palaiseau", r"saclay", r"evry", r"cergy", r"roissy", r"orly", r"rungis",
    r"greater paris", r"region de paris", r"paris et peripherie",
    r"creteil", r"villejuif", r"vitry sur seine", r"maisons alfort", r"antony", r"le plessis robinson",
    r"montigny le bretonneux", r"elancourt", r"plaisir", r"poissy", r"argenteuil", r"pontoise", r"osny",
    r"aulnay sous bois", r"rosny sous bois", r"villepinte", r"tremblay en france", r"romainville", r"champigny sur marne",
    r"fresnes", r"thiais", r"les ulis", r"orsay", r"bretigny sur orge", r"corbeil essonnes", r"lisses", r"melun",
    r"serris", r"chessy", r"montevrain", r"collegien", r"torcy", r"rambouillet", r"le chesnay\w*", r"chambourcy",
    r"les mureaux", r"les clayes sous bois", r"saint maur des fosses", r"ivry", r"le pre saint gervais", r"bagnolet",
    r"les lilas", r"le kremlin bicetre", r"cachan", r"chatenay malabry", r"sceaux", r"bourg la reine", r"fontenay aux roses",
    r"chaville", r"ville d avray", r"garches", r"vaucresson", r"marnes la coquette", r"la celle saint cloud",
    r"le vesinet", r"chatou", r"croissy sur seine", r"houilles", r"sartrouville", r"maisons laffitte", r"bezons",
    r"nogent", r"joinville le pont", r"saint denis la plaine", r"la plaine saint denis", r"epinay sur seine",
    r"stains", r"drancy", r"le blanc mesnil", r"bondy", r"noisy le sec", r"villemomble", r"gagny", r"neuilly sur marne",
    r"chelles", r"lognes", r"noisiel", r"bussy saint georges", r"cergy pontoise", r"eragny", r"herblay\w*",
    r"franconville", r"ermont", r"eaubonne", r"sannois", r"enghien les bains", r"saint gratien", r"montmorency",
    r"sarcelles", r"gonesse", r"goussainville", r"roissy en france", r"wissous", r"chilly mazarin", r"longjumeau",
    r"savigny sur orge", r"juvisy sur orge", r"athis mons", r"viry chatillon", r"draveil", r"ris orangis",
    r"courcouronnes", r"saint quentin", r"trappes", r"guyancourt", r"voisins le bretonneux", r"buc", r"jouy en josas",
    r"velizy villacoublay", r"le chesnay rocquencourt",
    r"75\d{3}", r"77\d{3}", r"78\d{3}", r"91\d{3}", r"92\d{3}", r"93\d{3}", r"94\d{3}", r"95\d{3}",
])
# Suisse : toutes les villes comptent (Genève surtout). Formes françaises, anglaises, allemandes, italiennes.
SWISS_LOC = _rx([
    r"switzerland", r"suisse", r"schweiz", r"svizzera", r"swiss",
    r"geneva", r"geneve", r"genf", r"ginevra", r"zurich", r"zuerich", r"lausanne", r"zug", r"zoug", r"baar",
    r"basel", r"bale", r"basle", r"lugano", r"bern", r"berne", r"nyon", r"lucerne", r"luzern",
    r"winterthur", r"winterthour", r"st gallen", r"sankt gallen", r"saint gall", r"fribourg", r"neuchatel",
    r"vaud", r"pfaffikon", r"chiasso", r"carouge", r"plan les ouates", r"cointrin",
])
SG_LOC = _rx([r"singapore", r"singapour", r"singapura"])
# Londres : la ville et ses quartiers d'affaires (pas tout le Royaume-Uni)
LONDON_LOC = _rx([
    r"london", r"londres", r"londra", r"greater london", r"city of london", r"canary wharf", r"liverpool street",
    r"(?:ec|wc)[1-4][a-z]? \d[a-z]{2}", r"e14 \d[a-z]{2}",
])
# Quartiers de Londres : seulement avec un contexte britannique (Camden NJ, Westminster CO, Kensington MD existent)
LONDON_BOROUGH = _rx([r"mayfair", r"westminster", r"holborn", r"farringdon", r"shoreditch", r"southwark",
                      r"islington", r"camden", r"kensington", r"knightsbridge", r"belgravia", r"marylebone"])
UK_CTX = _rx([r"england", r"united kingdom", r"uk", r"royaume uni", r"angleterre", r"great britain"])
# Dublin : la ville et son comté (pas Dublin, Ohio / Californie)
DUBLIN_LOC = _rx([r"dublin", r"county dublin", r"co dublin", r"dun laoghaire", r"sandyford", r"ballsbridge",
                  r"irish financial services centre", r"ifsc"])
NOT_DUBLIN = _rx([r"united states", r"usa", r"ohio", r"california", r"virginia", r"georgia", r"pennsylvania",
                  r"texas", r"oh", r"ca"])
REGIONS = (("France", PARIS_LOC), ("Suisse", SWISS_LOC), ("Singapour", SG_LOC), ("Londres", LONDON_LOC),
           ("Dublin", DUBLIN_LOC))
REGION_NAMES = tuple(r for r, _ in REGIONS)
# Noms de ville affichés (premier motif trouvé dans le segment de lieu)
CITY_NAMES = [(re.compile(r"(?<![a-z0-9])(?:%s)(?![a-z0-9])" % rx), name) for rx, name in [
    (r"la defense", "La Défense"), (r"paris", "Paris"), (r"ile de france|idf", "Île-de-France"),
    (r"geneva|geneve|genf|ginevra", "Genève"), (r"zurich|zuerich", "Zurich"), (r"lausanne", "Lausanne"),
    (r"zug|zoug", "Zoug"), (r"baar", "Baar"), (r"basel|bale|basle", "Bâle"), (r"lugano", "Lugano"),
    (r"berne?", "Berne"), (r"nyon", "Nyon"), (r"lucerne|luzern", "Lucerne"),
    (r"winterthur|winterthour", "Winterthour"), (r"st gallen|sankt gallen|saint gall", "Saint-Gall"),
    (r"fribourg", "Fribourg"), (r"neuchatel", "Neuchâtel"), (r"pfaffikon", "Pfäffikon"),
    (r"switzerland|suisse|schweiz|svizzera|swiss", "Suisse"), (r"singapore|singapour|singapura", "Singapour"),
    (r"canary wharf", "Canary Wharf"), (r"london|londres|londra|greater london|city of london", "Londres"),
    (r"dublin|county dublin|co dublin|ifsc", "Dublin"),
]]

# ---------- Métiers ----------
CAT_PATTERNS = {
    "M&A / IBD": [
        r"mna", r"fusions?", r"fusions? (?:et |and )?acquisitions?", r"mergers?", r"investment banking", r"ibd",
        r"banque d affaires", r"banque conseil", r"corporate finance", r"finance d entreprise",
        r"ecm", r"dcm", r"equity capital markets?", r"debt capital markets?",
        r"leveraged finance", r"levfin", r"acquisition finance", r"financements? d acquisition",
        r"debt advisory", r"conseil en financement", r"restructuring", r"restructuration financiere",
        r"corporate advisory", r"financial advisory", r"coverage", r"origination", r"global advisory",
        r"sovereign advisory", r"financial sponsors?", r"sponsors coverage", r"fig",
        r"financial institutions? group", r"advisory (?:and )?(?:mna|m a)",
        r"corporate development", r"deal advisory", r"lead advisory", r"structured finance",
        r"financements? structures?", r"project finance", r"financements? de projets?", r"debt syndicate",
        r"acquisitions? cessions?", r"cessions? acquisitions?", r"valorisation d entreprises?", r"business valuation",
        r"corporate banking", r"banquier conseil", r"banking (?:off ?cycle|summer|spring|winter|autumn)",
        r"syndicated loans?", r"loan syndication", r"financements? syndiques?", r"loan sales",
        r"infra\w* (?:and )?(?:energy )?finance", r"charge e? d affaires financements?",
        r"financements? (?:aeronautiques?|aviation|d actifs|maritimes?|shipping)", r"aviation finance", r"asset finance",
        r"private capital advisory", r"primary capital advisory", r"private placements?", r"placements? prives",
        r"fundraising advisory", r"analyste fundraising", r"fundraising analysts?",
        # v7
        r"(?<!working )capital solutions", r"secondary advisory", r"aviation advisory",
        # v10 : Citi "Banking, Financing", PJT "Strategic Advisory", Jefferies "Private Fund Advisory", UBS "Global Banking",
        # Commerzbank "Syndicated Finance", CIMB "Wholesale Banking", UOB "Corporate Investments & Acquisitions"
        r"banking (?:and )?financing", r"strategic advisory", r"private funds? advisory", r"global banking",
        r"syndicated finance", r"wholesale banking", r"investments? (?:and )?acquisitions?",
        # v10 (échantillon de référence) : Macquarie "Generalist Advisory", Rothschild "Arrowpoint Advisory",
        # SGX "GSO, Debt & Equity"
        r"generalist advisory", r"arrowpoint\w*", r"debt (?:and )?equity",
        r"fund finance",  # financement de fonds en banque (ING) ; exclu chez un gérant (voir BANKS dans categorize)
    ],
    "Private Equity": [
        r"private equity", r"capital investissement", r"capital developpement", r"capital transmission",
        r"lbo", r"buy ?out", r"growth equity", r"private debt", r"dette privee", r"secondaires?",
        r"secondaries", r"fonds d investissement", r"investment analyst", r"analyste investissements?",
        r"charge d affaires (?:capital|investissement|private|fonds|pe|lbo|mezzanine)\w*", r"investment associate", r"investment team", r"equipe d investissement",
        r"investissement non cote", r"\bpe\b fund", r"charge e? d investissements?", r"chargee? d investissements?", r"gp stakes", r"gp solutions", r"gp led", r"continuation funds?",
        # v7
        r"private credit", r"real estate investments?(?! trusts?)", r"real estate private equity",
        # v10 : Blackstone Tactical Opportunities / Strategic Partners (secondaires), Castleton "Principal Investments",
        # Keppel "RE/DC/OneInfra Investment", Capstone "Investment Internship"
        r"tactical opportunities", r"blackstone strategic partners", r"principal investments?",
        r"(?:re|dc|oneinfra|direct) investments?",
    ],
    "Private Equity (faible)": [
        r"infrastructure", r"real assets", r"primaries", r"co ?invest\w*",
        r"fund of funds", r"fonds de fonds", r"portfolio operations", r"value creation", r"private markets?",
    ],
    "Venture Capital": [
        r"venture capital", r"venture", r"capital risque", r"vc", r"corporate venture",
        r"seed fund", r"start ?up investing",
    ],
    "Asset Management": [
        r"asset management", r"gestion d actifs", r"portfolio manag\w*", r"gestion de portefeuilles?",
        r"gerant", r"gerante", r"gerants", r"fund manag\w*", r"multi ?assets?", r"allocation d actifs",
        r"asset allocation", r"investment specialist", r"product specialist", r"buy ?side", r"hedge funds?",
        r"gestion (?:actions|obligataire|taux|diversifiee|credit|collective|alternative|multi ?gestion)",
        r"analyste gestion", r"gestion d investissements?", r"investment management",
        r"gestionnaire de portefeuilles?", r"investment solutions", r"fund selection", r"selection de fonds",
        r"investment research", r"buy ?side research", r"recherche (?:investissement|gestion)",
        r"high yield", r"multi ?gestion", r"multi ?management", r"fund analysts?",
        # v7
        r"investment managers?", r"portfolio construction", r"investment analysis",
        r"(?:sustainable|responsible) investing",
        r"investment intern(?:ships?|s)?",  # v10 : Capstone "Investment Internship", Altor "Investment Intern"
        r"(?:uk|europe|european|credit|growth|direct|private|global) investing",  # v10 : Sixth Street "UK Investing"
        r"investment direct(?:ing|ors?)",  # v10 : Fidelity International "Investment Directing" (spécialistes produits)
    ],
    "Sales & Trading": [
        r"sales trading", r"sales and trading", r"sales traders?", r"traders?", r"trading",
        r"global markets?", r"markets", r"capital markets", r"marches de capitaux", r"marches financiers",
        r"salle des? marches?", r"fixed income", r"ficc", r"equities", r"equity derivatives",
        r"derivatives", r"derives", r"fx", r"forex", r"rates", r"institutional sales", r"cross asset",
        r"obligataire", r"primary bonds", r"syndicate", r"syndication", r"primary markets?",
        r"marches? primaires?", r"prime brokerage", r"securities lending", r"repo",
        r"equity research", r"credit research", r"fixed income research", r"macro research",
        r"recherche (?:actions|credit|macro\w*|economique|marches?|obligataire|taux|obligations?)",
        r"exchange traded", r"etfs?", r"research analysts?",
    ],
}
CAT_RX = {k: _rx(v) for k, v in CAT_PATTERNS.items()}

# "Sales" seul : accepté seulement avec un contexte marchés
SALES_RX = _rx([r"sales", r"vente", r"vendeur", r"vendeuse"])
MARKET_CTX = _rx([
    r"markets?", r"marches?", r"trading", r"fixed income", r"ficc", r"equit(?:y|ies)", r"actions",
    r"derivatives?", r"derives", r"fx", r"forex", r"change", r"rates", r"taux", r"credit",
    r"commodit(?:y|ies)", r"matieres premieres", r"bonds?", r"obligataire", r"cross asset",
    r"institutional", r"institutionnels?", r"structured products", r"produits structures",
    r"flow", r"investors?", r"investisseurs", r"etfs?", r"options", r"futures", r"swaps?", r"convertibles?",
    r"repo", r"money markets?", r"monetaire", r"obligations", r"exchange traded",
])

ADMIN_ASSISTANT = [
    r"assistante?s? (?:de |d |du )?(?:direction|administrati\w*|gestion|equipe|polyvalent\w*|comptable|juridique|"
    r"rh|ressources humaines|communication|marketing|bureau|accueil|achats?|facturation|paie|recrutement)",
    r"(?:executive|office|personal|administrative|admin|team|legal|hr|marketing|management|board|ceo|division|"
    r"department|events?) assistants?",
    r"secretaires?", r"secretariat", r"office manager", r"receptionist\w*", r"hote\w* d accueil",
]
SUPPORT_EXCLUDE = [
    r"trade support", r"trading support", r"it support", r"support informatique", r"support utilisateurs?",
    r"support technique", r"technical support", r"customer support", r"user support", r"support applicatif",
    r"application support", r"production support",
]

# Métiers exclus (demande explicite : pas de structuring ni de quant)
ROLE_EXCLUDE = _rx([
    r"structuring", r"structureur", r"structureuse", r"structuration", r"structurer",
    r"quant", r"quants", r"quantitative?", r"quantitatif", r"quantitatives", r"strats?",
    r"risk", r"risks", r"risques?", r"compliance", r"conformite", r"audit", r"auditeur",
    r"transaction services", r"middle office", r"back office", r"operations", r"ops",
    r"it", r"developer", r"developpeur",
    r"developpeuse", r"engineer", r"engineering", r"ingenieur", r"ingenieure", r"data",
    r"software", r"devops", r"cyber\w*", r"juristes?", r"legal", r"avocats?", r"cabinet d avocats",
    r"lawyers?", r"counsel", r"droit", r"juridique", r"law", r"rh", r"hr", r"human resources", r"ressources humaines", r"recrutement",
    r"recruitment", r"talent (?:acquisition|management|sourcing|partner|development)", r"marketing",
    r"consultant\w*", r"consulting", r"conseil (?:en )?strategi\w*", r"strategy consult\w*", r"chief of staff", r"medias?", r"programmati\w*", r"digital trader\w*",
    r"trader\w* digital", r"social media", r"trader social", r"ads", r"advertising", r"publicite", r"adtech", r"paid media",
    r"superintend\w*",
    r"technicien\w*", r"inspecteur\w*", r"inspection", r"securite financiere", r"fraude", r"fraud",
    r"enseignant\w*", r"teacher", r"professeur", r"commercial banking", r"banque commerciale",
    r"conseil en strategie", r"communication", r"comptable", r"comptabilite",
    r"accounting", r"accountant", r"controle de gestion", r"controller", r"controleur", r"kyc",
    r"aml", r"lcb ft", r"product owner", r"project manager", r"chef de projet", r"moa", r"pmo",
    r"research scientist", r"ux research\w*", r"user research\w*", r"recherche et developpement",
    r"r and d", r"business developer", r"business development", r"bizdev",
    r"account executive", r"account manager", r"sdr", r"bdr", r"customer success",
    r"real estate", r"immobilier",
    r"wealth", r"patrimoine", r"gestion de patrimoine", r"private bank", r"banque privee",
    r"gestion de fortune", r"gerante?s? de fortune", r"gestionnaires? de fortune", r"vermogensverwaltung",
    r"privatbank\w*", r"private banking",
    r"retail", r"reseau", r"agence", r"conseiller clientele", r"actuar\w*", r"model validation", r"model risk",
    r"validation des modeles", r"valuation control", r"cloud", r"network\w*", r"systemes?", r"systems", r"sre",
    r"product control", r"tax", r"fiscal\w*", r"strategy consulting",
    r"esg analyst", r"esg", r"trade finance", r"financement du commerce", r"commerce international",
    r"financement export", r"credit documentaire", r"trade services",
    # v7 : faux positifs constatés (banque de transaction, surveillance/contrôle, IR, ESG, conseil, fund finance chez un GP)
    r"cash management", r"transaction banking", r"surveillance", r"supervision", r"controls?", r"controles?",
    r"investor relations", r"relations investisseurs",
    r"sustainability(?! (?:investment|investing|investments|fund|funds|portfolio|equity|research|analyst))", r"connectivity", r"business management",
    r"performance improvement", r"fund finance", r"asset manag\w* (?:bureaux|commerces?|residentiel\w*|logistique)",
] + ADMIN_ASSISTANT + SUPPORT_EXCLUDE)
# Exceptions : ne pas exclure ces formulations utiles
ROLE_EXCLUDE_EXCEPTIONS = re.compile(
    r"(?<![a-z0-9])(?:structured products sales|sales structured products|"
    r"credit sales|equity research sales|capital risques?|capital risk|portfolio operations|"
    r"structur\w* (?:lbo|d acquisition|acquisition|financ\w*)|(?:leveraged|acquisition) finance structur\w*|"
    r"financements? structures?|structured finance|"
    r"sales (?:and )?trading (?:and )?structur\w*|trading (?:and )?structur\w*|sales (?:and )?structur\w*|"
    r"structur\w* (?:and )?(?:sales|trading)\w*|"
    # v7 : syndication de crédits (IBD) ; immobilier côté investissement chez un investisseur
    r"loans? structur\w*|real estate investments?(?! trusts?)|private equity real estate|real estate private equity|"
    r"real estate fund manag\w*)(?![a-z0-9])"
)


def _zone(norm_text):
    """Zone d'un texte. Londres passe après les autres zones (offre "London; Paris" rangée en France), et n'est
    retenue que si le texte ne parle pas d'un autre London (Ontario, Connecticut...)."""
    reg = _first_region(norm_text, ("France", "Suisse", "Singapour"))
    if reg:
        return reg
    if not NOT_LONDON.search(norm_text) and (
            LONDON_LOC.search(norm_text) or (LONDON_BOROUGH.search(norm_text) and UK_CTX.search(norm_text))):
        return "Londres"
    if DUBLIN_LOC.search(norm_text) and not NOT_DUBLIN.search(norm_text):
        return "Dublin"
    return None


def _first_region(norm_text, allowed=REGION_NAMES):
    """Région dont la première mention apparaît le plus tôt dans le texte normalisé."""
    best = None
    for name, rx in REGIONS:
        if name not in allowed:
            continue
        m = rx.search(norm_text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), name)
    return best[1] if best else None


# "New London, CT", "London, Ontario", "East London" (Afrique du Sud), "Camden, NJ"... : pas Londres
NOT_LONDON = _rx([r"new london", r"east london", r"london ontario", r"ontario", r"canada", r"united states", r"usa",
                  r"south africa", r"kentucky", r"ohio", r"connecticut", r"new jersey", r"colorado", r"london on"])


def region_of(location, title=""):
    """'France' (Paris et Île-de-France uniquement), 'Suisse', 'Singapour', 'Londres' ou None."""
    loc = normalize(location)
    reg = _zone(loc)
    if reg:
        return reg
    # Lieu vide, télétravail ou juste "France" : on regarde si le titre nomme une ville d'une zone
    stripped = loc.strip()
    if stripped in ("", "remote", "hybrid", "teletravail", "on site"):
        return _zone(normalize(title))
    if stripped in ("france", "fr"):
        return _first_region(normalize(title), ("France",))
    return None


def is_paris(location, title=""):
    return region_of(location, title) == "France"


def _city_name(norm_text):
    if CITY_NAMES[0][0].search(norm_text):  # "Paris La Défense" : La Défense, plus précis
        return CITY_NAMES[0][1]
    best = None
    for rx, name in CITY_NAMES:
        m = rx.search(norm_text)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), name)
    return best[1] if best else None


def city_of(location, title=""):
    """Ville lisible pour l'affichage ("Paris", "La Défense", "Genève", "Zurich", "Singapour"...)."""
    reg = region_of(location, title)
    if not reg:
        return ""
    allowed = (reg,)
    for seg in re.split(r"[,;/|·•()\[\]\n]+|\s[-–]\s", location or ""):
        n = normalize(seg)
        if not _first_region(n, allowed):
            continue
        name = _city_name(n)
        if name:
            return name
        clean = re.sub(r"\b\d{4,6}\b", " ", seg)
        clean = re.sub(r"\s+", " ", clean).strip(" -–")
        if clean:
            return clean
    return _city_name(normalize(title)) or ("Paris" if reg == "France" else reg)


def intern_status(title, description="", employment_type=""):
    """Retourne 'yes', 'no' ou 'unknown'."""
    t = INTERN_EXPERIENCE.sub(" ", normalize(title))
    if CONTRACT_EXCLUDE.search(t):
        return "no"
    if INTERN_TITLE.search(t):
        return "yes"
    if NOT_INTERN_TITLE.search(t) and not ASSISTANT_TITLE.search(t):
        return "no"  # VP, associate, graduate programme, CDI... sans le mot "stage"
    et = normalize(employment_type)
    if et.strip():
        if re.search(r"(?<![a-z])(internship|internships|stage|intern|interns|attachment|praktikum)(?![a-z])", et):
            return "yes"
        if re.search(r"(?<![a-z])(full time|temps plein|contract|contractor|temporary|part time|permanent|cdi|cdd|"
                     r"freelance|mid senior level|entry level|associate|director|executive)(?![a-z])", et):
            return "no"  # type de contrat indiqué par l'employeur : ce n'est pas un stage
    if description:
        d = STAGE_FALSE.sub(" ", normalize(description))
        if INTERN_DESC.search(d):
            return "yes"
        return "no"
    return "unknown"


# Commodities : tout poste lié aux matières premières (trading, analyse de marché, origination,
# opérations, trade finance, affrètement...), seules les fonctions support restent exclues.
# Mots sans ambiguïté
COMMO_RX = _rx([
    r"commodit(?:y|ies)", r"matieres? premieres?", r"energy trading", r"energy markets?",
    r"marches? de l energie", r"marches? de l electricite", r"marches? du gaz", r"power trading",
    r"power markets?", r"gas trading", r"gas markets?", r"agri commodit\w*", r"affretement",
    r"chartering", r"charterers?", r"bunkers?", r"carbon trading", r"marches? (?:du )?carbone", r"emissions trading",
    r"energy (?:origination|analyst|trader|trading|sales|markets?)", r"trading (?:d )?energie", r"negoce",
    r"carbon markets?", r"rohstoff\w*", r"energiehandel\w*", r"stromhandel\w*", r"gashandel\w*",
    r"freight (?:trad\w*|markets?|analysts?|derivatives|desk)", r"shipping markets?", r"ship ?brok\w*", r"tankers?",
    r"(?:oil|gas|power|lng|lpg|metals?|crude|freight|coal|softs|grains?) (?:market )?analysts?",
])
# Mots ambigus (électricien, consultant Oil & Gas, transitaire...) : comptent seulement avec un contexte marché
COMMO_WEAK = _rx([
    r"oil", r"petrole", r"petroliers?", r"crude", r"metals?", r"metaux", r"freight", r"power", r"gas", r"gaz",
    r"electricity", r"electricite", r"emissions?", r"carbon", r"lng", r"gnl", r"energy", r"energie", r"shipping",
    r"coal", r"charbon", r"grains?", r"sugar", r"coffee", r"cocoa", r"cotton", r"copper", r"aluminium", r"iron ore",
    r"softs",
])
COMMO_CTX = _rx([
    r"trading", r"trad(?:er|ers|eur|euse|euses)", r"markets?", r"marches?", r"negoce", r"origination", r"hedg\w*",
    r"couverture", r"pricing", r"schedul\w*", r"desk", r"operators?", r"operations?", r"chartering",
])


def _commo(t):
    return bool(COMMO_RX.search(t) or (COMMO_WEAK.search(t) and COMMO_CTX.search(t)))


# Grandes maisons de négoce : leurs stages d'analyse, de trading ou d'opérations relèvent des Commodities
COMMO_HOUSES = _rx([
    r"vitol", r"trafigura", r"gunvor", r"glencore", r"mercuria", r"cargill", r"louis dreyfus", r"ldc", r"cofco\w*",
    r"bunge", r"olam", r"ofi", r"wilmar", r"axpo", r"castleton", r"hartree", r"litasco", r"socar", r"sucden",
    r"ameropa", r"alvean", r"engelhart", r"etg", r"bb energy", r"sinochem", r"unipec", r"petrochina", r"freepoint",
    r"edf trading", r"uniper", r"totalenergies trading", r"shell trading", r"bp trading", r"koch supply",
    r"koch",  # v7 : "Koch" (Koch Supply & Trading, Singapour)
    r"klesch",  # v10 : Klesch Group (raffinage, métaux, négoce), programme d'analystes
])
COMMO_HOUSE_ROLE = _rx([
    r"analysts?", r"analyste", r"research", r"recherche", r"trading", r"traders?", r"operations?", r"operators?",
    r"freight", r"chartering", r"markets?", r"originat\w*", r"scheduler\w*",
    r"shipping", r"traffic",  # v7 : opérations physiques (traffic = logistique d'un négociant)
])
HOUSE_EXCLUDE = _rx([r"risk", r"risks", r"control\w*", r"finance", r"treasury", r"tresorerie", r"credit", r"gen ?ai", r"ai",
                     r"digital", r"strategy", r"sustainability", r"esg", r"business analyst"])


COMMO_HARD_EXCLUDE = _rx([
    r"it", r"developer", r"developpeur", r"developpeuse", r"engineer", r"engineering", r"ingenieur",
    r"ingenieure", r"data", r"software", r"devops", r"cyber\w*", r"juriste", r"legal", r"avocat", r"lawyer",
    r"rh", r"hr", r"human resources", r"ressources humaines", r"recrutement", r"recruitment", r"talent",
    r"marketing", r"communication", r"comptable", r"comptabilite", r"accounting", r"accountant", r"audit",
    r"auditeur", r"compliance", r"conformite", r"kyc", r"aml", r"quant", r"quants", r"quantitative?",
    r"structuring", r"structureur", r"maintenance", r"hse", r"securite", r"safety", r"achats?",
    r"procurement", r"acheteur", r"acheteuse",
    r"controle de gestion", r"controller", r"tax", r"fiscal\w*", r"retail", r"station",
    r"power ?bi", r"power ?point", r"power ?apps", r"power ?automate", r"technicien\w*", r"chantier",
    r"electricien\w*", r"installat\w*", r"bureau d etudes", r"btp", r"consultant\w*", r"consulting",
    r"superintend\w*", r"forwarding", r"transitaire", r"credit analysts?", r"analyste credit", r"customs",
    r"business develop\w*", r"bizdev", r"conseil en strategie", r"strategy", r"strategie",
    # v7 : risque et contrôle exclus aussi côté matières premières ; "gestionnaire" = back/middle office
    r"risk", r"risks", r"risques?", r"controls?", r"controles?", r"gestionnaires?(?! de portefeuilles?)",
] + ADMIN_ASSISTANT + SUPPORT_EXCLUDE)
IBD_STRICT = _rx([r"mna", r"fusions?", r"mergers?", r"investment banking", r"ibd", r"banque d affaires",
                  r"corporate finance", r"private equity", r"capital investissement", r"lbo", r"buy ?out",
                  r"venture capital", r"capital risque", r"vc", r"ecm", r"dcm", r"leveraged finance",
                  r"coverage", r"restructuring", r"debt advisory", r"acquisition finance", r"project finance",
                  r"financements? de projets?", r"structured finance"])
# Financement d'acquisition / LevFin : métier de banque d'affaires, même si le titre cite "LBO"
LEVFIN_RX = _rx([r"leveraged finance", r"levfin", r"acquisition finance", r"financements? d acquisitions?",
                 r"structured finance", r"financements? structures?", r"debt advisory"])
# Assistant gérant : métier de gestion d'actifs, pas un poste d'assistanat
AM_ASSISTANT_OK = re.compile(
    r"(?<![a-z0-9])(?:assistante? (?:de |du |au |aux )?(?:gerants?|gerantes?|portfolio manag\w*|fund manag\w*)"
    # v7 : "Assistant de Gestion Fixed Income", "Assistant Gestion de Portefeuilles Obligataires" (Lazard Frères Gestion)
    r"|assistante? (?:de )?gestion(?= (?:de portefeuilles?|fixed income|obligataire|actions|taux|credit|diversifiee|"
    r"multi|alternative|quantitative|flexible|convertibles?)(?![a-z0-9])))(?![a-z0-9])")


# ---------- Langues exigées (allemand, mandarin) ----------
LANG_WORDS = {
    "allemand": _rx([r"german", r"deutsch", r"deutschkenntnisse\w*", r"allemand", r"tedesco", r"swiss german",
                     r"schweizerdeutsch", r"suisse allemand"]),
    "mandarin": _rx([r"mandarin", r"chinese", r"chinois", r"putonghua", r"zhongwen"]),
}
LANG_CONTEXT = _rx([
    r"language\w*", r"langues?", r"linguisti\w*", r"speak\w*", r"spoken", r"written", r"writing", r"fluen\w*",
    r"proficien\w*", r"bilingu\w*", r"native", r"natif", r"native speaker", r"parler", r"parle\w*", r"maitris\w*",
    r"courant\w*", r"converse", r"conversational", r"verbal", r"oral", r"ecrit", r"command", r"mother tongue",
    r"deutschkenntnisse\w*", r"sprachkenntnisse\w*", r"kenntnisse", r"sprache\w*", r"muttersprache\w*",
    r"deutsch", r"allemand", r"mandarin", r"read", r"lire", r"english", r"anglais", r"englisch", r"french",
    r"francais", r"franzosisch", r"italian", r"italien", r"spanish", r"espagnol", r"cantonese", r"malay",
])
LANG_REQUIRED = _rx([
    r"fluen\w*", r"native", r"natif", r"native speaker", r"proficien\w*", r"bilingu\w*", r"mandatory", r"required",
    r"requirements?", r"requis\w*", r"essential", r"must", r"necessary", r"necessaire", r"indispensable",
    r"obligatoire", r"exige\w*", r"imperati\w*", r"courant\w*", r"maitris\w*", r"excellent\w*", r"strong",
    r"good command", r"command of", r"business level", r"professional working", r"full professional",
    r"written and spoken", r"spoken and written", r"ecrit et oral", r"oral et ecrit", r"able to speak",
    r"able to converse", r"able to communicate", r"ability to (?:speak|converse|communicate)", r"to liaise",
    r"fliessend\w*", r"verhandlungssicher\w*", r"muttersprache\w*", r"zwingend", r"erforderlich",
    r"vorausgesetzt", r"sehr gute\w*", r"ausgezeichnete\w*", r"stilsicher\w*", r"need to", r"needs to",
    r"speak mandarin", r"speak german", r"parler allemand", r"parler mandarin",
    r"proficiency", r"qualifications?",
])
LANG_PLUS = _rx([
    r"plus", r"advantage\w*", r"asset", r"atout", r"apprecie\w*", r"souhait\w*", r"nice to have", r"bonus",
    r"prefer\w*", r"ideally", r"idealement", r"desirable", r"desired", r"beneficial", r"benefit", r"would be",
    r"serait", r"wunschenswert", r"von vorteil", r"vorteil\w*", r"idealerweise", r"optional\w*", r"not required",
    r"not mandatory", r"not necessary", r"pas obligatoire", r"non obligatoire", r"pas necessaire", r"additional",
    r"other languages?", r"further languages?", r"autres? langues?", r"helpful", r"welcome", r"bienvenu\w*",
    r"good to have", r"valued", r"an edge",
])
# "allemand ou anglais", "German or French" : une alternative existe, la langue n'est pas exigée
LANG_ALTERNATIVE = re.compile(
    r"(?<![a-z0-9])(?:german|deutsch|allemand|mandarin|chinese|chinois)\s+(?:and ?/ ?)?(?:or|ou|oder)\s+"
    r"(?:\w+\s+){0,2}(?:french|francais|franzosisch|english|anglais|englisch|italian|italien|spanish|espagnol)"
    r"|(?:french|francais|franzosisch|english|anglais|englisch|italian|italien)\s+(?:or|ou|oder)\s+"
    r"(?:\w+\s+){0,2}(?:german|deutsch|allemand|mandarin|chinese|chinois)(?![a-z0-9])")
GERMAN_STOP = re.compile(r"(?<![a-zäöüß])(?:und|der|die|das|mit|für|wir|sie|ihre|ihr|eine|einen|einem|sind|werden|"
                         r"oder|bei|auf|zu|im|ist|unser|unsere|von|als|sowie|deine|du|dich)(?![a-zäöüß])", re.I)


def language_required(description):
    """'allemand' ou 'mandarin' si l'offre exige cette langue (pas si c'est « un plus »), sinon None."""
    if not description:
        return None
    raw = str(description)
    words = re.findall(r"[A-Za-zÀ-ÿß]+", raw)
    if len(words) >= 40 and len(GERMAN_STOP.findall(raw)) / len(words) > 0.08:
        return "allemand"  # offre rédigée en allemand
    if len(re.findall(r"[\u4e00-\u9fff]", raw)) >= 20:
        return "mandarin"  # offre rédigée en chinois
    for sent in re.split(r"[.!?;\n\r•·▪●◦\u2022]+|<br\s*/?>|</?(?:li|p|div|ul)[^>]*>", raw):
        n = normalize(sent)
        if len(n) < 6:
            continue
        for lang, rx in LANG_WORDS.items():
            if not rx.search(n):
                continue
            if not LANG_CONTEXT.search(rx.sub(" ", n)) and not re.search(r"(?<![a-z])(?:deutsch|allemand|mandarin)(?![a-z])", n):
                continue  # "Chinese clients", "marché allemand" : pas une langue
            if LANG_ALTERNATIVE.search(n):
                continue
            # "English and German required, French a plus" : on juge chaque morceau de phrase
            parts = [normalize(x) for x in re.split(r"[,:()\[\]]| - | – ", sent)] if LANG_PLUS.search(n) else [n]
            for part in parts:
                if rx.search(part) and LANG_REQUIRED.search(part) and not LANG_PLUS.search(part):
                    return lang
                if rx.search(part) and not LANG_PLUS.search(part) and LANG_REQUIRED.search(n) and len(parts) == 1:
                    return lang
    return None


# Exclusions qui ne valent pas pour un groupe sectoriel de banque d'affaires ou de la recherche actions
SECTOR_WORDS = {"retail", "real estate", "immobilier", "media", "medias", "telecom", "network", "networks"}
SECTOR_OK = _rx([r"investment banking", r"mna", r"ibd", r"coverage", r"equity research\w*", r"recherche actions",
                 r"corporate finance", r"consumer"])


# ---------- v7 : règles fondées sur l'employeur ----------
# Cabinets d'avocats : un "Stage Corporate M&A" y est un stage juridique
LAW_FIRMS = _rx([
    r"avocats?", r"law", r"law firm", r"eversheds\w*", r"dentons", r"linklaters", r"clifford chance", r"allen (?:and )?overy",
    r"a and o shearman", r"freshfields", r"cms francis lefebvre", r"gide", r"bredin prat", r"darrois\w*",
    r"white and case", r"latham\w*", r"kirkland\w*", r"skadden", r"hogan lovells", r"baker mckenzie", r"ashurst\w*",
    r"herbert smith\w*", r"jones day", r"willkie\w*", r"weil gotshal\w*", r"sullivan and cromwell", r"cleary gottlieb\w*",
    r"davis polk", r"simpson thacher", r"mayer brown", r"dla piper", r"norton rose\w*", r"fieldfisher", r"bird and bird",
    r"osborne clarke", r"august debouzy", r"de pardieu\w*", r"jeantet", r"fidal", r"racine", r"mcdermott\w*", r"orrick",
    r"gibson dunn", r"paul hastings", r"goodwin procter", r"proskauer", r"reed smith", r"watson farley\w*",
    r"stephenson harwood", r"holman fenwick\w*", r"rajah and tann", r"allen and gledhill", r"wongpartnership",
    r"drew and napier", r"lenz and staehelin", r"homburger", r"bar and karrer", r"baer and karrer", r"schellenberg wittmer",
    r"niederer kraft\w*", r"walder wyss", r"pestalozzi", r"kellerhals\w*",
])
# Conseil : "Value Creation" chez PwC = conseil opérationnel ; cabinets d'économie (litiges) = conseil
CONSULTING_FIRMS = _rx([r"pwc\w*", r"pricewaterhouse\w*", r"deloitte", r"ey", r"ernst and young", r"kpmg",
                        r"alvarez and marsal", r"bcg", r"boston consulting\w*", r"mckinsey\w*", r"bain and company",
                        r"accenture", r"oliver wyman", r"roland berger", r"kearney"])
CONSULTING_ROLE = _rx([r"value creation", r"transformation", r"strategy", r"strategie"])
ECON_CONSULTING = _rx([r"analysis group", r"compass lexecon", r"cornerstone research", r"nera economic\w*",
                       r"charles river associates", r"oxera"])
# Banques : "fund finance" y est un métier de financement (IBD) ; "Sales"/"Research" seul = marchés
BANKS = _rx([
    r"ing", r"ing bank", r"bnp paribas", r"societe generale", r"natixis", r"credit agricole cib", r"hsbc", r"barclays",
    r"deutsche bank", r"j ?p ?morgan\w*", r"jpmorgan\w*", r"goldman sachs", r"morgan stanley", r"bank of america",
    r"citi", r"citigroup", r"ubs", r"mufg", r"mizuho", r"smbc", r"nomura", r"dbs", r"ocbc", r"uob",
    r"standard chartered", r"commerzbank\w*", r"rbc", r"jefferies", r"wells fargo", r"bbva", r"santander",
    r"unicredit", r"abn amro", r"rabobank", r"macquarie",
])
# Gérants (AM, hedge funds, PE/VC) : intitulés génériques ou par secteur qui ne nomment pas le métier
AM_COMPANY = _rx([r"asset management", r"asset managers", r"investment managers?", r"investment management",
                  r"capital management", r"gestion"])
INVEST_HOUSES = {  # employeur -> catégorie
    "Asset Management": _rx([r"brevan howard", r"blackrock", r"comgest", r"tikehau\w*", r"graham capital\w*", r"capula\w*",
                             r"verition\w*", r"capstone investment\w*", r"point72", r"millennium", r"citadel",
                             r"balyasny", r"marshall wace", r"man group"]),
    "Private Equity": _rx([r"partners group", r"clubfunding\w*", r"la caisse", r"cdpq", r"3i", r"sixth street"]),
    "Venture Capital": _rx([r"sg growth capital"]),
}
# Banques d'affaires : intitulé réduit à une équipe sectorielle ("Industrials Team", "Telecom & Tech")
IB_HOUSES = _rx([r"evercore", r"lazard", r"rothschild and co", r"houlihan lokey", r"pjt\w*", r"moelis\w*",
                 r"perella\w*", r"centerview\w*", r"greenhill\w*", r"lincoln international",
                 r"natixis corporate (?:and )?investment banking"])
# Boutiques dont un stage "générique" est forcément en banque d'affaires
IB_GENERIC_HOUSES = _rx([r"evercore", r"pjt\w*", r"moelis\w*", r"perella\w*", r"centerview\w*", r"greenhill\w*",
                         r"lincoln international", r"raine"])
GENERIC_INVEST_HOUSES = _rx([r"brevan howard", r"blackrock", r"comgest", r"partners group", r"la caisse", r"cdpq", r"3i",
                             r"graham capital\w*", r"sixth street", r"capula\w*", r"verition\w*", r"capstone investment\w*",
                             r"point72", r"millennium", r"citadel", r"balyasny", r"marshall wace", r"man group"])
# v10 : stage générique "Analyst" / "Placement" chez une maison ci-dessus (Partners Group "Summer Analyst Program")
GENERIC_CORE_NOISE = re.compile(r"(?<![a-z0-9])(?:analysts?|financial|placement|united|kingdom|uk|ireland)(?![a-z0-9])")
# v10 : en banque, "Global Research", "Client Sales", "Corporates Sales", "Sales Analyst" = marchés
BANK_SR_CORE = r"(?:(?:global|client|corporates?|institutional) )*(?:sales|research)"
# v10 : gérants de private equity dont l'immobilier est un métier d'investissement (Blackstone REPE, Carlyle)
PE_HOUSES = _rx([r"blackstone", r"carlyle", r"kkr", r"apollo", r"tpg", r"brookfield", r"eqt", r"cvc", r"bain capital",
                 r"partners group", r"ardian", r"tikehau\w*"])
PE_RE_ROLE = _rx([r"real estate (?:partners|secondaries|debt|acquisitions?|investments?|equity)", r"real estate intern\w*"])
INVEST_ROLE = _rx([r"financial analysts?", r"analystes? financi\w*", r"credit analysts?", r"analystes? credit"])
VC_SECTORS = r"healthcare|life sciences?|green|bio|economy|hardware|next|gen|consumer|industrials?|deep ?tech|fintech|semiconductors?"
IB_SECTORS = (r"industrials?|consumer|retail|healthcare|tmt|telecom\w*|media|technology|tech|energy|power|infrastructure|"
              r"fig|financial|institutions?|real|estate|natural|resources|transport|environment|industry|groups?|"
              r"generalist|sponsors?|chemicals|business|services|diversified")
# Mots sans contenu métier : années, contrat, durée, lieux, "programme", "team"...
TITLE_NOISE = re.compile(
    r"(?<![a-z0-9])(?:\d+\w*|stages?|stagiaires?|interns?|internships?|off|cycle|offcycle|summer|spring|winter|autumn|"
    r"fall|seasonal|programs?|programmes?|talent|team|students?|graduates?|offers?|offres?|opportunita|di|de|du|d|des|"
    r"la|le|les|the|of|a|and|for|en|in|et|to|h|f|m|w|x|n|b|start|date|starting|year|years|months?|mois|jan\w*|feb\w*|"
    r"mar\w*|apr\w*|may|jun\w*|jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*|janvier|fevrier|mars|avril|mai|juin|juillet|"
    r"aout|septembre|octobre|novembre|decembre|paris|france|geneva|geneve|zurich|switzerland|suisse|singapore|"
    r"singapour|london|londres|emea|apac|apej|asia|europe|i|ii)(?![a-z0-9])")


def _title_core(t):
    """Intitulé normalisé sans les mots vides (contrat, dates, lieux) ni la liste de lieux BlackRock."""
    t = re.sub(r" location .*$", " ", t)
    return re.sub(r"\s+", " ", TITLE_NOISE.sub(" ", t)).strip()


def _only(core, words):
    return bool(core) and re.fullmatch(r"(?:(?:%s) ?)+" % words, core) is not None


def _house_category(t, company):
    """Catégorie déduite de l'employeur quand l'intitulé ne nomme pas le métier (ou None)."""
    if not company:
        return None
    c = normalize(company)
    core = _title_core(t)
    # v10 : sans les mots du nom de l'employeur ni "analyst"/"placement"/pays
    gcore = core
    for w in set(c.split()):
        if len(w) >= 3:
            gcore = re.sub(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(w), " ", gcore)
    gcore = re.sub(r"\s+", " ", GENERIC_CORE_NOISE.sub(" ", gcore)).strip()
    if BANKS.search(c) and (core in ("sales", "research") or re.fullmatch(BANK_SR_CORE, gcore)):
        return "Sales & Trading"
    if IB_HOUSES.search(c) and _only(core, IB_SECTORS):
        return "M&A / IBD"
    if IB_GENERIC_HOUSES.search(c) and not gcore:
        return "M&A / IBD"
    for cat, rx in INVEST_HOUSES.items():
        if rx.search(c) and (INVEST_ROLE.search(t) or _only(core, VC_SECTORS)
                             or (not gcore and GENERIC_INVEST_HOUSES.search(c))):
            return cat
    if AM_COMPANY.search(c) and INVEST_ROLE.search(t):
        return "Asset Management"
    return None


def categorize(title, company=""):
    """Renvoie (categorie, raison_exclusion). categorie=None si hors périmètre."""
    t = normalize(title)
    c = normalize(company)
    if company and LAW_FIRMS.search(c):
        return None, "métier exclu (cabinet d avocats)"
    if company and (ECON_CONSULTING.search(c) or (CONSULTING_FIRMS.search(c) and CONSULTING_ROLE.search(t))):
        return None, "métier exclu (conseil)"
    if company and COMMO_HOUSES.search(normalize(company)) and COMMO_HOUSE_ROLE.search(t) \
            and not COMMO_HARD_EXCLUDE.search(t) and not HOUSE_EXCLUDE.search(t):
        return "Commodities", None
    if _commo(t):
        m = COMMO_HARD_EXCLUDE.search(t)
        if m:
            return None, "métier exclu (%s)" % m.group(0).strip()
        # "M&A Oil & Gas" reste du M&A ; "origination" ou "coverage" seuls restent des Commodities
        if IBD_STRICT.search(t):
            if LEVFIN_RX.search(t):
                return "M&A / IBD", None
            for cat in ("Private Equity", "Venture Capital", "M&A / IBD"):
                if CAT_RX[cat].search(t):
                    return cat, None
        return "Commodities", None
    t = AM_ASSISTANT_OK.sub(" gerant ", t)
    t_for_excl = ROLE_EXCLUDE_EXCEPTIONS.sub(" ", t)
    if SECTOR_OK.search(t):  # "Investment Banking, Consumer Retail Group", "Equity Research Immobilier"
        for w in SECTOR_WORDS:
            t_for_excl = re.sub(r"(?<![a-z0-9])%s(?![a-z0-9])" % w, " ", t_for_excl)
    if company and PE_HOUSES.search(c) and PE_RE_ROLE.search(t):  # v10 : immobilier côté investissement chez un GP
        t_for_excl = re.sub(r"(?<![a-z0-9])real estate(?![a-z0-9])", " ", t_for_excl)
    if company and BANKS.search(c):  # "Fund Finance" en banque = financement de fonds (IBD), pas la finance d'un GP
        t_for_excl = re.sub(r"(?<![a-z0-9])fund finance(?![a-z0-9])", " ", t_for_excl)
    m = ROLE_EXCLUDE.search(t_for_excl)
    if m:
        return None, "métier exclu (%s)" % m.group(0).strip()
    if LEVFIN_RX.search(t):
        return "M&A / IBD", None
    if company and PE_HOUSES.search(c) and PE_RE_ROLE.search(t):
        return "Private Equity", None
    # Ordre : PE et VC avant M&A (un "stage investissement PE" ne doit pas finir en IBD)
    for cat in ("Private Equity", "Venture Capital", "Asset Management", "M&A / IBD", "Private Equity (faible)",
                "Sales & Trading"):
        if CAT_RX[cat].search(t):
            # "private equity" contient "equity" : géré car S&T vérifié après PE
            return ("Private Equity" if cat == "Private Equity (faible)" else cat), None
    if SALES_RX.search(t) and MARKET_CTX.search(t):
        return "Sales & Trading", None
    house = _house_category(t, company)
    if house:
        return house, None
    return None, "métier hors périmètre"


def classify(title, location, description="", employment_type="", extra_include=None, extra_exclude=None, company=""):
    """Décision complète. Renvoie dict(ok, category, intern, reason, summer, region)."""
    t = normalize(title)
    region = region_of(location, title)
    if extra_exclude and any(normalize(w).strip() and normalize(w) in t for w in extra_exclude):
        return dict(ok=False, category=None, intern="no", reason="mot exclu (config)", summer=False, region=region)
    if region is None:
        return dict(ok=False, category=None, intern="?", reason="hors zone", summer=False, region=None)
    cat, why = categorize(title, company)
    if cat is None and extra_include:
        if any(normalize(w).strip() and normalize(w) in t for w in extra_include):
            cat, why = "Autre (mot-clé perso)", None
    if cat is None:
        return dict(ok=False, category=None, intern="?", reason=why, summer=False, region=region)
    st = intern_status(title, description, employment_type)
    summer = bool(SUMMER_TITLE.search(t))
    if st == "no":
        return dict(ok=False, category=cat, intern="no", reason="pas un stage", summer=summer, region=region)
    lang = language_required(description)
    if lang:
        return dict(ok=False, category=cat, intern=st, reason="langue requise (%s)" % lang, summer=summer, region=region)
    return dict(ok=(st == "yes"), category=cat, intern=st,
                reason=None if st == "yes" else "stage à confirmer", summer=summer, region=region)


def dedup_key(company, title, region="France"):
    """Clé de doublon. Inchangée pour la France (clés déjà enregistrées), suffixée par la zone sinon."""
    t = normalize(title)
    t = re.sub(r"(?<![a-z0-9])(h f|f h|m f|f m|h f x|x h f|hf|fh|m w d|f h x|2026|2027|2028)(?![a-z0-9])", " ", t)
    t = re.sub(r"(?<![a-z0-9])(stage|stagiaire|intern|internship|off cycle|offcycle|praktikum|praktikant|"
               r"praktikantin)(?![a-z0-9])", " ", t)
    key = re.sub(r"\s+", " ", normalize(company).strip() + "|" + t.strip())
    return key if (region or "France") == "France" else key + "|" + region
