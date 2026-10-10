"""Filtrage des offres : stage/off-cycle + zone (Paris, Suisse, Singapour) + IBD (M&A, PE, VC), S&T, AM, Commodities.

Tout se joue sur du texte normalisé (minuscules, sans accents, ponctuation -> espaces).
Les listes sont volontairement explicites pour pouvoir être ajustées dans config.json.
"""
import re
import unicodedata

# À incrémenter à chaque changement de règles : les offres déjà écartées sont alors réexaminées.
FILTER_VERSION = 5


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
])
SUMMER_TITLE = _rx([r"summer"])
# Contrats explicitement exclus
CONTRACT_EXCLUDE = _rx([
    r"alternance", r"alternant", r"alternante", r"apprenti", r"apprentie", r"apprentissage",
    r"apprenticeship", r"v i e", r"volontariat international", r"cdi", r"cdd",
    r"contrat pro", r"contrat de professionnalisation", r"work ?study", r"phd", r"doctorat",
    # Allemand : étudiant salarié, apprentissage (Lehre / Lernende)
    r"werkstudent\w*", r"lehrstelle\w*", r"lernende[nr]?", r"lehrling\w*",
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
    r"(?<![a-z0-9])(?:\w+ ){0,3}internships? (?:and |or )?(?:work |relevant )?experiences?(?![a-z0-9])")
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
REGIONS = (("France", PARIS_LOC), ("Suisse", SWISS_LOC), ("Singapour", SG_LOC))
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
]]

# ---------- Métiers ----------
CAT_PATTERNS = {
    "M&A / IBD": [
        r"mna", r"fusions?", r"fusions? (?:et |and )?acquisitions?", r"mergers?", r"investment banking", r"ibd",
        r"banque d affaires", r"banque conseil", r"corporate finance", r"finance d entreprise",
        r"ecm", r"dcm", r"equity capital markets", r"debt capital markets",
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
    ],
    "Private Equity": [
        r"private equity", r"capital investissement", r"capital developpement", r"capital transmission",
        r"lbo", r"buy ?out", r"growth equity", r"private debt", r"dette privee", r"secondaires?",
        r"secondaries", r"fonds d investissement", r"investment analyst", r"analyste investissements?",
        r"charge d affaires (?:capital|investissement|private|fonds|pe|lbo|mezzanine)\w*", r"investment associate", r"investment team", r"equipe d investissement",
        r"investissement non cote", r"\bpe\b fund", r"gp stakes", r"gp solutions", r"gp led", r"continuation funds?",
    ],
    "Private Equity (faible)": [
        r"infrastructure", r"real assets", r"fund finance", r"primaries", r"co ?invest\w*",
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
    ],
    "Sales & Trading": [
        r"sales trading", r"sales and trading", r"sales traders?", r"traders?", r"trading",
        r"global markets?", r"markets", r"capital markets", r"marches de capitaux", r"marches financiers",
        r"salle des? marches?", r"fixed income", r"ficc", r"equities", r"equity derivatives",
        r"derivatives", r"derives", r"fx", r"forex", r"rates", r"institutional sales", r"cross asset",
        r"obligataire", r"primary bonds", r"syndicate", r"syndication", r"primary markets?",
        r"marches? primaires?", r"prime brokerage", r"securities lending", r"repo",
        r"equity research", r"credit research", r"fixed income research", r"macro research",
        r"recherche (?:actions|credit|macro\w*|economique|marches?|obligataire|taux)",
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
    r"lawyers?", r"droit", r"juridique", r"law", r"rh", r"hr", r"human resources", r"ressources humaines", r"recrutement",
    r"recruitment", r"talent (?:acquisition|management|sourcing|partner|development)", r"marketing",
    r"consultant\w*", r"consulting", r"chief of staff", r"medias?", r"programmati\w*", r"digital trader\w*",
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
] + ADMIN_ASSISTANT + SUPPORT_EXCLUDE)
# Exceptions : ne pas exclure ces formulations utiles
ROLE_EXCLUDE_EXCEPTIONS = re.compile(
    r"(?<![a-z0-9])(?:structured products sales|sales structured products|"
    r"credit sales|equity research sales|capital risques?|capital risk|portfolio operations|"
    r"structur\w* (?:lbo|d acquisition|acquisition|financ\w*)|(?:leveraged|acquisition) finance structur\w*|"
    r"financements? structures?|structured finance|"
    r"sales (?:and )?trading (?:and )?structur\w*|trading (?:and )?structur\w*|sales (?:and )?structur\w*|"
    r"structur\w* (?:and )?(?:sales|trading)\w*)(?![a-z0-9])"
)


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


def region_of(location, title=""):
    """'France' (Paris et Île-de-France uniquement), 'Suisse', 'Singapour' ou None."""
    loc = normalize(location)
    reg = _first_region(loc)
    if reg:
        return reg
    # Lieu vide, télétravail ou juste "France" : on regarde si le titre nomme une ville d'une zone
    stripped = loc.strip()
    if stripped in ("", "remote", "hybrid", "teletravail", "on site"):
        return _first_region(normalize(title))
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
])
COMMO_HOUSE_ROLE = _rx([
    r"analysts?", r"analyste", r"research", r"recherche", r"trading", r"traders?", r"operations?", r"operators?",
    r"freight", r"chartering", r"markets?", r"origination", r"scheduler\w*",
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
AM_ASSISTANT_OK = re.compile(r"(?<![a-z0-9])assistante? (?:de |du |au |aux )?(?:gerants?|gerantes?|portfolio manag\w*|fund manag\w*)(?![a-z0-9])")


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
SECTOR_WORDS = {"retail", "real estate", "immobilier", "media", "medias", "telecom"}
SECTOR_OK = _rx([r"investment banking", r"mna", r"ibd", r"coverage", r"equity research\w*", r"recherche actions",
                 r"corporate finance", r"consumer"])


def categorize(title, company=""):
    """Renvoie (categorie, raison_exclusion). categorie=None si hors périmètre."""
    t = normalize(title)
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
    m = ROLE_EXCLUDE.search(t_for_excl)
    if m:
        return None, "métier exclu (%s)" % m.group(0).strip()
    if LEVFIN_RX.search(t):
        return "M&A / IBD", None
    # Ordre : PE et VC avant M&A (un "stage investissement PE" ne doit pas finir en IBD)
    for cat in ("Private Equity", "Venture Capital", "Asset Management", "M&A / IBD", "Private Equity (faible)",
                "Sales & Trading"):
        if CAT_RX[cat].search(t):
            # "private equity" contient "equity" : géré car S&T vérifié après PE
            return ("Private Equity" if cat == "Private Equity (faible)" else cat), None
    if SALES_RX.search(t) and MARKET_CTX.search(t):
        return "Sales & Trading", None
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
