"""Filtrage des offres : stage/off-cycle + Paris + IBD (M&A, PE, VC) ou Sales & Trading.

Tout se joue sur du texte normalisé (minuscules, sans accents, ponctuation -> espaces).
Les listes sont volontairement explicites pour pouvoir être ajustées dans config.json.
"""
import re
import unicodedata


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
    r"winter internship", r"autumn internship", r"fall internship", r"trainee",
])
SUMMER_TITLE = _rx([r"summer"])
# Contrats explicitement exclus
CONTRACT_EXCLUDE = _rx([
    r"alternance", r"alternant", r"alternante", r"apprenti", r"apprentie", r"apprentissage",
    r"apprenticeship", r"v i e", r"volontariat international", r"cdi", r"cdd",
    r"contrat pro", r"contrat de professionnalisation", r"work ?study", r"phd", r"doctorat",
])
# Faux positifs anglais/français de "stage" dans les descriptions (early stage, etc.)
STAGE_FALSE = re.compile(
    r"(?<![a-z0-9])(?:early|growth|late|later|seed|any|every|all|this|that|next|first|"
    r"second|final|each|multi|mid|pre|post|clinical|development|developpement|commercial|"
    r"advanced|initial|current|same|various|different|critical|key|new|young)\s+stages?(?![a-z0-9])"
)
INTERN_DESC = re.compile(
    r"(?<![a-z0-9])(?:stagiaires?|internships?|interns?|off ?cycle|cesure|gap year|"
    r"convention de stage|stage de \d+|stage d une duree|stage a pourvoir|"
    r"duree du stage|offre de stage|stage de fin d etudes|stage (?:de )?(?:\d+|six|quatre|cinq) mois)(?![a-z0-9])"
)

# ---------- Lieu ----------
PARIS_LOC = _rx([
    r"paris", r"ile de france", r"idf", r"la defense", r"puteaux", r"courbevoie", r"neuilly",
    r"neuilly sur seine", r"levallois", r"levallois perret", r"boulogne", r"boulogne billancourt",
    r"issy les moulineaux", r"saint denis", r"montrouge", r"nanterre", r"clichy", r"saint cloud",
    r"rueil malmaison", r"suresnes", r"saint ouen", r"vincennes", r"charenton", r"ivry sur seine",
    r"75\d{3}", r"92\d{3}",
])

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
    ],
    "Private Equity": [
        r"private equity", r"capital investissement", r"capital developpement", r"capital transmission",
        r"lbo", r"buy ?out", r"growth equity", r"private debt", r"dette privee", r"secondaires?",
        r"secondaries", r"fonds d investissement", r"investment analyst", r"analyste investissements?",
        r"charge d affaires (?:capital|investissement|private|fonds|pe|lbo|mezzanine)\w*", r"investment associate", r"investment team", r"equipe d investissement",
        r"investissement non cote", r"\bpe\b fund",
    ],
    "Venture Capital": [
        r"venture capital", r"venture", r"capital risque", r"vc", r"corporate venture",
        r"seed fund", r"start ?up investing",
    ],
    "Sales & Trading": [
        r"sales trading", r"sales and trading", r"sales traders?", r"traders?", r"trading",
        r"global markets?", r"markets", r"capital markets", r"marches de capitaux", r"marches financiers",
        r"salle des? marches?", r"fixed income", r"ficc", r"equities", r"equity derivatives",
        r"derivatives", r"derives", r"fx", r"forex", r"rates", r"institutional sales", r"cross asset",
        r"obligataire", r"primary bonds", r"syndicate", r"syndication",
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
    r"flow", r"investors?", r"investisseurs",
])

# Métiers exclus (demande explicite : pas de structuring ni de quant)
ROLE_EXCLUDE = _rx([
    r"structuring", r"structureur", r"structureuse", r"structuration", r"structurer",
    r"quant", r"quants", r"quantitative?", r"quantitatif", r"quantitatives", r"strats?",
    r"risk", r"risks", r"risques?", r"compliance", r"conformite", r"audit", r"auditeur",
    r"transaction services", r"middle office", r"back office", r"operations", r"ops",
    r"trade support", r"trading support", r"support", r"it", r"developer", r"developpeur",
    r"developpeuse", r"engineer", r"engineering", r"ingenieur", r"ingenieure", r"data",
    r"software", r"devops", r"cyber", r"cybersecurity", r"juriste", r"legal", r"avocat",
    r"lawyer", r"rh", r"hr", r"human resources", r"ressources humaines", r"recrutement",
    r"recruitment", r"talent", r"marketing", r"communication", r"comptable", r"comptabilite",
    r"accounting", r"accountant", r"controle de gestion", r"controller", r"controleur", r"kyc",
    r"aml", r"lcb ft", r"product owner", r"project manager", r"chef de projet", r"moa", r"pmo",
    r"research", r"recherche", r"business developer", r"business development", r"bizdev",
    r"account executive", r"account manager", r"sdr", r"bdr", r"customer success",
    r"assistant", r"assistante", r"office manager", r"real estate", r"immobilier",
    r"wealth", r"patrimoine", r"gestion de patrimoine", r"private bank", r"banque privee",
    r"retail", r"reseau", r"agence", r"conseiller clientele", r"actuar\w*", r"model\w*", r"valuation control",
    r"product control", r"tax", r"fiscal\w*", r"strategy consulting",
    r"esg analyst", r"esg", r"trade finance", r"financement du commerce", r"commerce international",
    r"financement export", r"credit documentaire", r"trade services",
])
# Exceptions : ne pas exclure ces formulations utiles
ROLE_EXCLUDE_EXCEPTIONS = re.compile(
    r"(?<![a-z0-9])(?:structured products sales|sales structured products|"
    r"credit sales|equity research sales|capital risques?|capital risk|"
    r"sales (?:and )?trading (?:and )?structur\w*|trading (?:and )?structur\w*|sales (?:and )?structur\w*|"
    r"structur\w* (?:and )?(?:sales|trading)\w*)(?![a-z0-9])"
)


def is_paris(location, title=""):
    loc = normalize(location)
    if PARIS_LOC.search(loc):
        return True
    # Lieu vide ou juste "France" : on accepte seulement si le titre mentionne Paris
    stripped = loc.strip()
    if stripped in ("", "france", "fr", "remote", "hybrid"):
        return bool(PARIS_LOC.search(normalize(title)))
    return False


def intern_status(title, description="", employment_type=""):
    """Retourne 'yes', 'no' ou 'unknown'."""
    t = normalize(title)
    if CONTRACT_EXCLUDE.search(t):
        return "no"
    if INTERN_TITLE.search(t):
        return "yes"
    et = normalize(employment_type)
    if et.strip():
        if re.search(r"(?<![a-z])(internship|stage|intern)(?![a-z])", et):
            return "yes"
        if re.search(r"(?<![a-z])(full time|temps plein|contract|temporary|part time|cdi|cdd)(?![a-z])", et) \
                and not description:
            return "no"
    if description:
        d = STAGE_FALSE.sub(" ", normalize(description))
        if INTERN_DESC.search(d):
            return "yes"
        return "no"
    return "unknown"


def categorize(title):
    """Renvoie (categorie, raison_exclusion). categorie=None si hors périmètre."""
    t = normalize(title)
    t_for_excl = ROLE_EXCLUDE_EXCEPTIONS.sub(" ", t)
    m = ROLE_EXCLUDE.search(t_for_excl)
    if m:
        return None, "métier exclu (%s)" % m.group(0).strip()
    # Ordre : PE et VC avant M&A (un "stage investissement PE" ne doit pas finir en IBD)
    for cat in ("Private Equity", "Venture Capital", "M&A / IBD", "Sales & Trading"):
        if CAT_RX[cat].search(t):
            # "private equity" contient "equity" : géré car S&T vérifié après PE
            return cat, None
    if SALES_RX.search(t) and MARKET_CTX.search(t):
        return "Sales & Trading", None
    return None, "métier hors périmètre"


def classify(title, location, description="", employment_type="", extra_include=None, extra_exclude=None):
    """Décision complète. Renvoie dict(ok, category, intern, reason, summer)."""
    t = normalize(title)
    if extra_exclude and any(normalize(w).strip() and normalize(w) in t for w in extra_exclude):
        return dict(ok=False, category=None, intern="no", reason="mot exclu (config)", summer=False)
    if not is_paris(location, title):
        return dict(ok=False, category=None, intern="?", reason="hors Paris", summer=False)
    cat, why = categorize(title)
    if cat is None and extra_include:
        if any(normalize(w).strip() and normalize(w) in t for w in extra_include):
            cat, why = "Autre (mot-clé perso)", None
    if cat is None:
        return dict(ok=False, category=None, intern="?", reason=why, summer=False)
    st = intern_status(title, description, employment_type)
    summer = bool(SUMMER_TITLE.search(t))
    if st == "no":
        return dict(ok=False, category=cat, intern="no", reason="pas un stage", summer=summer)
    return dict(ok=(st == "yes"), category=cat, intern=st,
                reason=None if st == "yes" else "stage à confirmer", summer=summer)


def dedup_key(company, title):
    t = normalize(title)
    t = re.sub(r"(?<![a-z0-9])(h f|f h|m f|f m|h f x|x h f|hf|fh|m w d|f h x|2026|2027|2028)(?![a-z0-9])", " ", t)
    t = re.sub(r"(?<![a-z0-9])(stage|stagiaire|intern|internship|off cycle|offcycle)(?![a-z0-9])", " ", t)
    return re.sub(r"\s+", " ", normalize(company).strip() + "|" + t.strip())
