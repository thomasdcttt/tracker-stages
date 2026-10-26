#!/usr/bin/env python3
"""Tracker de stages off-cycle / césure à Paris, en Suisse, à Singapour et à Londres : IBD (M&A, PE, VC), S&T, AM, Commodities.

Usage :
    python tracker.py              surveillance continue (notifications + tableau de bord)
    python tracker.py --check      diagnostic : teste chaque source sans rien enregistrer
    python tracker.py --test-notif envoie une notification de test
    python tracker.py --once       un seul passage puis arrêt
    python tracker.py --reset      efface la mémoire des offres (repart de zéro)
"""
import argparse
import copy
import json
import os
import random
import re
import sys
import time
import traceback
import urllib.parse
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# Console Windows / lancement sans console (pythonw) : jamais de plantage sur un affichage
for _name in ("stdout", "stderr"):
    _s = getattr(sys, _name)
    if _s is None:
        setattr(sys, _name, open(os.devnull, "w", encoding="utf-8"))
    else:
        try:
            _s.reconfigure(errors="replace")
        except Exception:
            pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dashboard  # noqa: E402
import filters  # noqa: E402
import notify  # noqa: E402
import sources  # noqa: E402
from store import Store  # noqa: E402

DATA = os.path.join(HERE, "data")
CONFIG_PATH = os.path.join(HERE, "config.json")
DB_PATH = os.path.join(DATA, "offres.db")
DASH_PATH = os.path.join(DATA, "tableau_de_bord.html")
PRIORITY_PATH = os.path.join(DATA, "prioritaires.json")
LOG_PATH = os.path.join(DATA, "tracker.log")

DEFAULT_CONFIG = {
    "interval_minutes": 10,
    "linkedin": {
        "enabled": True,
        "location": "Paris, Île-de-France, France",
        "past_seconds": 604800,
        "pages_per_query": 1,
        "pause_between_queries": [2, 4],
        "pause_between_pages": [1.5, 3],
        "detail_limit_per_cycle": 30,
        # Balayage de TOUS les stages publiés à Paris (filtre LinkedIn « Stage »), à chaque passage
        "sweep_all": True,
        "sweep_all_seconds": 21600,
        "sweep_all_pages": 10,
        # Balayages par thème, sur les stages publiés depuis 24 h
        "sweep_seconds": 86400,
        "sweep_pages": 2,
        "sweeps": [
            "finance", "banque", "bank", "marchés", "markets", "trading", "sales", "investissement",
            "investment", "M&A", "private equity", "venture capital", "asset management", "gestion",
            "commodities", "énergie", "energy", "analyste", "analyst", "fund",
        ],
        # Nombre maximal de requêtes de recherche par passage (les recherches restantes passent au suivant)
        "max_search_requests": 80,
        "queries": [
            "stage M&A", "M&A internship", "stage fusions acquisitions", "stage banque d'affaires",
            "investment banking intern", "stage investment banking", "stage corporate finance",
            "stage financement d'acquisition", "leveraged finance internship", "stage ECM", "stage DCM",
            "off-cycle internship", "off cycle internship Paris", "stage césure finance",
            "stage private equity", "private equity internship", "stage capital investissement", "stage LBO",
            "stage venture capital", "venture capital internship", "stage capital risque",
            "stage sales trading", "sales and trading internship", "stage salle des marchés", "stage trading",
            "stage trader", "assistant trader", "sales assistant markets", "stage sales", "stage vendeur",
            "global markets internship", "stage marchés de capitaux", "stage fixed income", "stage equity sales",
            "stage dérivés", "stage FX", "stage taux",
            "stage asset management", "asset management internship", "stage gestion de portefeuille",
            "stage assistant gérant", "portfolio management internship", "stage gestion d'actifs",
            "stage commodities", "commodities internship", "stage matières premières", "energy trading internship",
            "stage marchés de l'énergie", "stage trading énergie", "stage power gas", "stage métaux",
            "stage pétrole trading", "stage freight", "stage négoce",
        ],
        # Zones couvertes. France : lieu ci-dessus, sweeps et queries ci-dessus. Suisse et Singapour : balayage de
        # tous les stages récents (filtre « Stage ») à chaque passage + recherches en rotation avec celles de Paris.
        "regions": {
            "France": {"enabled": True, "location": "Paris, Île-de-France, France"},
            "Suisse": {
                "enabled": True, "location": "Switzerland",
                "sweep_all": True, "sweep_all_seconds": 21600, "sweep_all_pages": 5,
                "stock_keywords": ["finance", "investment banking", "M&A", "corporate finance", "corporate development", "private equity", "venture capital", "trading", "markets", "sales trading", "investment", "asset management", "hedge fund", "broker", "commodities", "capital markets"], "stock_pages": 5,
                "sweeps": ["finance", "M&A", "investment banking", "corporate finance", "corporate development", "private equity", "venture capital", "investment", "asset management", "fund", "markets", "trading", "sales", "broker", "equity research", "credit", "capital markets", "commodities", "energy", "shipping", "analyst", "banking"], "sweep_seconds": 86400, "sweep_pages": 2,
                "queries": [
                    "corporate M&A intern", "M&A analyst intern", "corporate development intern", "corporate finance internship", "debt advisory intern", "equity capital markets intern", "broker intern", "boutique investment bank intern", "financial analyst intern", "summer internship finance 2027",
                    "investment banking intern", "M&A intern", "private equity intern", "venture capital intern",
                    "sales and trading intern", "global markets intern", "summer analyst", "off-cycle internship",
                    "commodities intern", "commodity trading intern", "energy trading intern",
                    "asset management intern", "portfolio management intern", "hedge fund intern",
                    "equity research intern", "corporate finance intern",
                    "investment analyst intern", "buy side intern", "investment management summer internship",
                    "asset management summer internship", "equity analyst intern", "fixed income intern",
                    "private credit intern", "infrastructure investment intern", "investment intern",
                    "private markets intern", "fund management intern",
                    "stage M&A Genève", "stage trading Genève", "stage finance Genève",
                    "Praktikum Investment Banking", "Praktikum Trading", "Praktikum Asset Management",
                    "Praktikum Rohstoffhandel",
                ],
            },
            "Singapour": {
                "enabled": True, "location": "Singapore",
                "sweep_all": True, "sweep_all_seconds": 21600, "sweep_all_pages": 5,
                "stock_keywords": ["finance", "investment banking", "M&A", "corporate finance", "corporate development", "private equity", "venture capital", "trading", "markets", "sales trading", "investment", "asset management", "hedge fund", "broker", "commodities", "capital markets"], "stock_pages": 5,
                "sweeps": ["finance", "M&A", "investment banking", "corporate finance", "corporate development", "private equity", "venture capital", "investment", "asset management", "fund", "markets", "trading", "sales", "broker", "equity research", "credit", "capital markets", "commodities", "energy", "shipping", "analyst", "banking"], "sweep_seconds": 86400, "sweep_pages": 2,
                "queries": [
                    "corporate M&A intern", "M&A analyst intern", "corporate development intern", "corporate finance internship", "debt advisory intern", "equity capital markets intern", "broker intern", "boutique investment bank intern", "financial analyst intern", "summer internship finance 2027",
                    "investment banking intern", "M&A intern", "private equity intern", "venture capital intern",
                    "sales and trading intern", "global markets intern", "summer analyst", "off-cycle internship",
                    "commodities intern", "commodity trading intern", "energy trading intern",
                    "asset management intern", "portfolio management intern", "hedge fund intern",
                    "equity research intern", "corporate finance intern",
                    "investment analyst intern", "buy side intern", "investment management summer internship",
                    "asset management summer internship", "equity analyst intern", "fixed income intern",
                    "private credit intern", "infrastructure investment intern", "investment intern",
                    "private markets intern", "fund management intern",
                ],
            },
            "Londres": {
                "enabled": True, "location": "London, England, United Kingdom",
                "sweep_all": True, "sweep_all_seconds": 21600, "sweep_all_pages": 6, "backfill_pages": 40,
                "stock_keywords": ["finance", "investment banking", "M&A", "corporate finance", "corporate development", "private equity", "venture capital", "trading", "markets", "sales trading", "investment", "asset management", "hedge fund", "broker", "commodities", "capital markets", "equity research", "credit", "summer analyst", "placement"], "stock_pages": 8,
                "sweeps": ["finance", "M&A", "mergers acquisitions", "investment banking", "corporate finance", "corporate development", "private equity", "venture capital", "investment", "investor", "asset management", "fund", "hedge fund", "markets", "trading", "trader", "sales", "broking", "broker", "equity research", "credit", "capital markets", "debt", "commodities", "energy", "shipping", "analyst", "banking", "placement", "summer analyst"], "sweep_seconds": 86400, "sweep_pages": 3,
                "queries": [
                    "corporate M&A intern", "M&A analyst intern", "corporate development internship", "strategy and M&A internship", "corporate finance internship", "transaction advisory internship", "debt advisory intern", "restructuring internship", "equity capital markets internship", "corporate broking internship", "stockbroking internship", "broker internship", "interdealer broker intern", "shipbroking internship", "commodity broker intern", "mid-market investment bank internship", "boutique investment bank internship", "investment banking off-cycle internship", "industrial placement finance", "placement year investment banking", "12 month placement finance", "spring internship finance", "summer internship finance 2027", "financial analyst intern", "treasury intern", "investor relations intern",
                    "investment banking intern", "investment banking summer analyst", "M&A intern",
                    "off-cycle internship", "summer internship 2027", "private equity intern", "venture capital intern",
                    "sales and trading intern", "global markets summer analyst", "commodities intern",
                    "commodity trading intern", "energy trading intern", "asset management intern",
                    "portfolio management intern", "hedge fund intern", "equity research intern",
                    "corporate finance intern", "leveraged finance intern", "debt capital markets intern",
                    "bp summer internship trading", "supply trading shipping internship", "energy trading summer internship",
                    "BNP Paribas internship London", "Societe Generale internship London", "Morgan Stanley summer analyst",
                    "UBS internship London", "Standard Chartered internship", "Citadel internship", "Brevan Howard internship",
                    "investment analyst intern", "buy side intern", "investment management summer internship",
                    "asset management summer internship", "equity analyst intern", "fixed income intern",
                    "private credit intern", "infrastructure investment intern", "investment intern",
                    "private markets intern", "fund management intern",
                ],
            },
            "Dublin": {
                "enabled": True, "location": "Dublin, County Dublin, Ireland",
                "sweep_all": True, "sweep_all_seconds": 21600, "sweep_all_pages": 3, "backfill_pages": 15,
                "stock_keywords": ["finance", "investment banking", "M&A", "corporate finance", "corporate development", "private equity", "venture capital", "trading", "markets", "sales trading", "investment", "asset management"], "stock_pages": 3,
                "sweeps": ["finance", "M&A", "investment banking", "corporate finance", "corporate development", "private equity", "venture capital", "investment", "asset management", "fund", "markets", "trading", "sales", "broker", "equity research", "credit", "capital markets", "commodities", "energy", "shipping", "analyst", "banking"], "sweep_seconds": 86400, "sweep_pages": 2,
                "queries": [
                    "corporate M&A intern", "M&A analyst intern", "corporate development intern", "corporate finance internship", "debt advisory intern", "equity capital markets intern", "broker intern", "boutique investment bank intern", "financial analyst intern", "summer internship finance 2027",
                    "investment banking intern", "summer analyst", "off-cycle internship", "summer internship 2027",
                    "private equity intern", "sales and trading intern", "global markets intern", "asset management intern",
                    "fund management intern", "investment analyst intern", "aviation finance intern", "aircraft leasing intern",
                    "commodities intern", "energy trading intern", "corporate finance intern", "hedge fund intern",
                ],
            },
        },
    },
    "wttj": {
        "enabled": True,
        "hits_per_page": 100,
        "max_pages": 3,
        "recent_days": 30,
        "queries": [
            "M&A", "fusions acquisitions", "banque d'affaires", "corporate finance", "private equity",
            "capital investissement", "LBO", "venture capital", "capital risque", "sales trading", "trading",
            "trader", "sales", "marchés financiers", "marchés de capitaux", "fixed income", "dérivés",
            "asset management", "gestion d'actifs", "gestion de portefeuille", "assistant gérant",
            "commodities", "matières premières", "énergie trading", "énergie", "négoce", "analyste financier",
            "investissement", "banque d'investissement", "finance de marché", "fonds",
        ],
        # Recherches par employeur : couvre toutes les offres de ces entreprises sur Welcome to the Jungle
        "companies": [
            "Natixis", "BPCE", "Société Générale", "BNP Paribas", "Crédit Agricole", "CACIB", "Crédit Mutuel",
            "CIC", "La Banque Postale", "Oddo BHF", "Rothschild", "Edmond de Rothschild", "Lazard", "Kepler Cheuvreux",
            "Bryan Garnier", "Alantra", "Clipperton", "Cambon Partners", "Messier", "DC Advisory", "Degroof Petercam",
            "Amundi", "AXA", "Carmignac", "Tikehau", "Eurazeo", "Ardian", "Wendel", "Bpifrance", "Ostrum", "Mirova",
            "LBP AM", "Groupama", "Sycomore", "DNCA", "La Financière de l'Echiquier", "Comgest", "Candriam",
            "Partech", "Idinvest", "Elaia", "Serena", "Alven", "Breega", "Eurazeo", "Andera", "Siparex", "Apax",
            "TotalEnergies", "Engie", "EDF", "Trafigura", "Vitol", "Mercuria", "Gunvor", "Louis Dreyfus", "Axpo",
            "Uniper", "Kpler", "Argus", "Vortexa", "CMA CGM",
        ],
    },
    "workday": {
        "enabled": True,
        "queries": ["internship", "intern", "summer internship", "summer analyst", "off-cycle", "placement", "stage",
                    "internship London", "internship Paris", "internship Singapore", "internship Zurich",
                    "internship Dublin"],
        "tenants": [
            {"company": "Barclays", "host": "barclays.wd3.myworkdayjobs.com", "tenant": "barclays",
             "site": "External_Career_Site_Barclays", "enabled": True},
            {"company": "Deutsche Bank", "host": "db.wd3.myworkdayjobs.com", "tenant": "db",
             "site": "DBWebsite", "enabled": True},
            {"company": "Citi", "host": "citi.wd5.myworkdayjobs.com", "tenant": "citi",
             "site": "2", "enabled": True},
        ],
    },
    # Sites carrières surveillés directement (en plus de LinkedIn). Types : workday, oracle, eightfold, html.
    "sites": [
        {"company": "J.P. Morgan", "type": "oracle", "host": "jpmc.fa.oraclecloud.com", "site": "CX_1001"},
        {"company": "Lazard", "type": "oracle", "host": "icbpjb.fa.ocs.oraclecloud.com", "site": "LazardProfessionalCareers"},
        {"company": "Lazard", "label": "Lazard (étudiants)", "type": "oracle", "host": "icbpjb.fa.ocs.oraclecloud.com", "site": "LazardStudentCareers"},
        {"company": "HSBC", "type": "eightfold", "host": "portal.careers.hsbc.com", "domain": "hsbc.com"},
        {"company": "HSBC", "label": "HSBC (early careers)", "type": "html", "url": "https://mycareer.hsbc.com/en_GB/external/SearchJobs/?listFilterMode=1&jobRecordsPerPage=50", "link_regex": "/en_GB/external/PipelineDetail/[^/\\\"]+/\\d+"},
        {"company": "Ardian", "type": "workday", "host": "ardian.wd103.myworkdayjobs.com", "tenant": "ardian", "site": "ArdianCareers"},
        {"company": "Rothschild & Co", "type": "html", "urls": ["https://www.rothschildandco.com/en/careers/students-and-graduates/opportunities/", "https://www.rothschildandco.com/en/careers/students-and-graduates/opportunities/?page=2", "https://www.rothschildandco.com/en/careers/students-and-graduates/opportunities/?taxonomy_1156=739"], "link_regex": "/careers/students-and-graduates/opportunities/[^/?#]+/?$"},
        {"company": "Rothschild & Co", "label": "Rothschild & Co (Workday)", "type": "workday", "host": "rothschildandco.wd3.myworkdayjobs.com", "tenant": "rothschildandco", "site": "Rothschildandco_Lateral"},
        {"company": "Crédit Agricole CIB", "type": "html", "url": "https://jobs.ca-cib.com/offre-de-emploi/liste-toutes-offres.aspx?all=1&mode=layer", "link_regex": "/offre-de-emploi/emploi-[^\\\"?#]+_\\d+\\.aspx"},
        {"company": "Evercore", "type": "html", "url": "https://evercore.tal.net/vx/lang-en-GB/mobile-0/channel-1/appcentre-ext/brand-6/candidate/jobboard/vacancy/2/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+"},
        {"company": "Amundi", "type": "html", "urls": ["https://jobs.amundi.com/job/list-of-all-jobs.aspx?all=1&mode=layer", "https://jobs.amundi.com/offre-de-emploi/liste-toutes-offres.aspx?all=1&mode=layer"], "link_regex": "/(?:job|offre-de-emploi)/(?:job|emploi)-[^\\\"?#]+_\\d+\\.aspx"},
        {"company": "TotalEnergies", "type": "html", "urls": ["https://jobs.totalenergies.com/fr_FR/careers/SearchJobs/stage", "https://jobs.totalenergies.com/en_US/careers/SearchJobs/intern", "https://jobs.totalenergies.com/fr_FR/careers/SearchJobs", "https://jobs.totalenergies.com/en_US/careers/SearchJobs/Singapore?listFilterMode=1&jobRecordsPerPage=20"], "link_regex": "/careers/JobDetail/[^/\\\"]+/\\d+"},
        {"company": "BlackRock", "type": "html", "urls": ["https://careers.blackrock.com/category/students-and-graduates-jobs/45831/9022304/1", "https://careers.blackrock.com/location/singapore-jobs/45831/1880251/4", "https://careers.blackrock.com/location/france-jobs/45831/3017382/2"], "link_regex": "/job/[^/\\\"]+/[^/\\\"]+/45831/\\d+"},
        {"company": "Comgest", "type": "html", "default_location": "Paris", "url": "https://www.comgest.com/en/about-us/our-people/careers/internship-offers"},
        {"company": "Blackstone", "label": "Blackstone (campus)", "type": "workday", "host": "blackstone.wd1.myworkdayjobs.com", "tenant": "blackstone", "site": "Blackstone_Campus_Careers"},
        {"company": "Fidelity International", "label": "Fidelity International (early careers)", "type": "html", "url": "https://fidelityinternational.tal.net/vx/lang-en-GB/mobile-0/brand-5/candidate/jobboard/vacancy/1/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+"},
        {"company": "Houlihan Lokey", "type": "workday", "host": "hl.wd1.myworkdayjobs.com", "tenant": "hl", "site": "Campus"},
        {"company": "Jefferies", "type": "html", "url": "https://jefferies.tal.net/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/xf-016c915b0a67/candidate/jobboard/vacancy/2/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+"},
        {"company": "Bank of America", "type": "html", "url": "https://bankcampuscareers.tal.net/vx/lang-en-GB/mobile-0/brand-4/xf-6f0048376f93/candidate/jobboard/vacancy/2/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+"},
        {"company": "Goldman Sachs", "type": "oracle", "host": "hdpc.fa.us2.oraclecloud.com", "site": "LateralHiring"},
        {"company": "Macquarie", "label": "Macquarie (graduates & interns)", "type": "html", "urls": ["https://recruitment.macquarie.com/en_US/careers/SearchJobs/?7959=%5B421070%2C421069%5D&7959_format=14495&listFilterMode=1&jobRecordsPerPage=9&jobOffset=0", "https://recruitment.macquarie.com/en_US/careers/SearchJobs/?7959=%5B421070%2C421069%5D&7959_format=14495&listFilterMode=1&jobRecordsPerPage=9&jobOffset=9", "https://recruitment.macquarie.com/en_US/careers/SearchJobs/?7959=%5B421070%2C421069%5D&7959_format=14495&listFilterMode=1&jobRecordsPerPage=9&jobOffset=18", "https://recruitment.macquarie.com/en_US/careers/SearchJobs/?7959=%5B421070%2C421069%5D&7959_format=14495&listFilterMode=1&jobRecordsPerPage=9&jobOffset=27"], "link_regex": "JobDetail\\?jobId=\\d+"},
        {"company": "Trafigura", "type": "workday", "host": "trafigura.wd3.myworkdayjobs.com", "tenant": "trafigura", "site": "TrafiguraCareerSite"},
        {"company": "Gunvor", "type": "workday", "host": "gunvor.wd3.myworkdayjobs.com", "tenant": "gunvor", "site": "Gunvor_Careers"},
        {"company": "Glencore", "type": "workday", "host": "glencorecorp.wd3.myworkdayjobs.com", "tenant": "glencorecorp", "site": "External"},
        {"company": "Shell", "type": "workday", "host": "shell.wd3.myworkdayjobs.com", "tenant": "shell", "site": "ShellCareers"},
        {"company": "Cargill", "type": "html", "urls": ["https://careers.cargill.com/en/location/switzerland-jobs/23251/2658434/2", "https://careers.cargill.com/en/location/singapore-jobs/23251/1880251-7535954-1880252/4"], "link_regex": "/en/job/[^/\\\"]+/[^/\\\"]+/23251/\\d+"},
        {"company": "COFCO International", "type": "html", "default_location": "Genève, Suisse", "url": "https://careers.cofcointernational.com/search/?q=&locationsearch=Geneva", "link_regex": "/job/[^/\\\"]+/\\d+/"},
        {"company": "Bunge", "type": "html", "urls": ["https://jobs.bunge.com/search/?q=&locationsearch=Geneva", "https://jobs.bunge.com/search/?q=&locationsearch=Singapore"], "link_regex": "/job/[^\\\"]+/\\d+/"},
        {"company": "Axpo", "type": "html", "default_location": "Baden, Switzerland", "urls": ["https://careers.axpo.com/jobs", "https://careers.axpo.com/jobs?query=intern", "https://careers.axpo.com/jobs?query=praktikum"], "link_regex": "/jobs/\\d+-[a-z0-9-]+"},
        {"company": "SGX Group", "type": "html", "url": "https://careers.sgx.com/search/?q=intern", "link_regex": "/job/[^\\\"]+/\\d+/"},
        {"company": "Julius Baer", "type": "workday", "host": "juliusbaer.wd3.myworkdayjobs.com", "tenant": "juliusbaer", "site": "External"},
        {"company": "UBP", "type": "oracle", "host": "iaadtu.fa.ocs.oraclecloud.eu", "site": "CX_1"},
        {"company": "Citi", "label": "Citi (Suisse, Singapour, Londres)", "type": "html", "urls": ["https://jobs.citi.com/location/switzerland-jobs/287/2658434/2", "https://jobs.citi.com/location/singapore-jobs/287/1880251/4", "https://jobs.citi.com/employment/london-england-united-kingdom-student-and-grad-programs-jobs/287/9378912/2635167-6269131-2648110-2643743/4"], "link_regex": "/job/[^/\\\"]+/[^/\\\"]+/287/\\d+"},
        {"company": "Partners Group", "type": "html", "url": "https://jobs.partnersgroup.com/search/?q=intern", "link_regex": "/job/[^/\\\"]+/\\d+/"},
        {"company": "Swiss Re", "type": "html", "url": "https://careers.swissre.com/search/?q=intern", "link_regex": "/job/[^/\\\"]+/\\d+/"},
        {"company": "Vontobel", "type": "html", "default_location": "Zurich, Switzerland", "url": "https://www.vontobel.com/en/about-vontobel/careers/open-positions/", "link_regex": "/careers/open-positions/\\d+-[a-z0-9-]+/?"},
        {"company": "LGT", "type": "html", "urls": ["https://www.lgt.com/ch-en/career/jobs", "https://www.lgt.com/ch-en/career/jobs/48662!jobSearch?pageNum=1", "https://www.lgt.com/ch-en/career/jobs/48662!jobSearch?pageNum=2", "https://www.lgt.com/ch-en/career/jobs/48662!jobSearch?pageNum=3", "https://www.lgt.com/ch-en/career/jobs/48662!jobSearch?pageNum=4", "https://www.lgt.com/ch-en/career/jobs/48662!jobSearch?pageNum=5"], "link_regex": "/career/jobs/[a-z0-9-]+-\\d+"},
        {"company": "DBS", "type": "workday", "host": "dbs.wd3.myworkdayjobs.com", "tenant": "dbs", "site": "DBS_Careers"},
        {"company": "Temasek", "type": "html", "url": "https://jobs.temasek.com.sg/search/?q=intern", "link_regex": "/job/[^\\\"]+/\\d+/"},
        {"company": "GIC", "type": "html", "url": "https://careers.gic.com.sg/search/?q=intern", "link_regex": "/job/[^\\\"]+/\\d+/?"},
        {"company": "Eastspring Investments", "type": "workday", "host": "prudential.wd3.myworkdayjobs.com", "tenant": "prudential", "site": "prudential_eastspring"},
        {"company": "Schroders", "type": "oracle", "host": "ekbq.fa.em2.oraclecloud.com", "site": "CX_2"},
        {"company": "Brookfield", "type": "workday", "host": "brookfield.wd5.myworkdayjobs.com", "tenant": "brookfield", "site": "brookfield"},
        {"company": "Bain Capital", "type": "workday", "host": "baincapital.wd1.myworkdayjobs.com", "tenant": "baincapital", "site": "External_Public"},
        {"company": "Lombard Odier", "type": "workday", "host": "lombardodier.wd3.myworkdayjobs.com", "tenant": "lombardodier", "site": "Lombard_Odier_Careers"},
        {"company": "Edmond de Rothschild", "type": "oracle", "host": "evht.fa.ocs.oraclecloud.eu", "site": "CX_7001", "site_number": "CX_7001"},
        {"company": "EFG International", "type": "oracle", "host": "fa-eqai-saasfaprod1.fa.ocs.oraclecloud.com", "site": "CX_1001", "site_number": "CX_1001"},
        {"company": "Garda Capital Partners", "type": "greenhouse", "board": "gardacp"},
        {"company": "Engelhart", "type": "greenhouse", "board": "engelhart"},
        {"company": "Kepler Cheuvreux", "type": "html", "url": "https://keplercheuvreux.teamtailor.com/jobs", "link_regex": "/jobs/\\d+-[a-z0-9-]+"},
        {"company": "DWS", "type": "workday", "host": "db.wd3.myworkdayjobs.com", "tenant": "db", "site": "DWSWebsite"},
        {"company": "ING", "label": "ING (France)", "type": "workday", "host": "ing.wd3.myworkdayjobs.com", "tenant": "ing", "site": "ICSFRADIR"},
        {"company": "ING", "label": "ING (global)", "type": "workday", "host": "ing.wd3.myworkdayjobs.com", "tenant": "ing", "site": "ICSGBLCOR"},
        {"company": "Point72", "type": "greenhouse", "board": "point72"},
        {"company": "Capital Group", "type": "workday", "host": "capgroup.wd1.myworkdayjobs.com", "tenant": "capgroup", "site": "capitalgroupcareers"},
        {"company": "MUFG", "type": "workday", "host": "mufgub.wd3.myworkdayjobs.com", "tenant": "mufgub", "site": "MUFG-Careers"},
        {"company": "SMBC", "label": "SMBC (Asie)", "type": "html", "default_location": "Singapore", "urls": ["https://careerasia.smbc.co.jp/SMBC/search/?q=&locationsearch=Singapore&startrow=0", "https://careerasia.smbc.co.jp/SMBC/search/?q=&locationsearch=Singapore&startrow=25", "https://careerasia.smbc.co.jp/SMBC/search/?q=&locationsearch=Singapore&startrow=50", "https://careerasia.smbc.co.jp/SMBC/search/?q=&locationsearch=Singapore&startrow=75", "https://careerasia.smbc.co.jp/SMBC/search/?q=&locationsearch=Singapore&startrow=100", "https://careerasia.smbc.co.jp/SMBC/search/?q=&locationsearch=Singapore&startrow=125"], "link_regex": "/SMBC/job/[^\\\"]+/\\d+/"},
        {"company": "Castleton Commodities", "type": "workday", "host": "osv-cci.wd1.myworkdayjobs.com", "tenant": "osv_cci", "site": "CCICareers"},
        {"company": "PJT Partners", "label": "PJT Partners (students)", "type": "workday", "host": "pjtpartners.wd1.myworkdayjobs.com", "tenant": "pjtpartners", "site": "Students"},
        {"company": "PJT Partners", "label": "PJT Partners (careers)", "type": "workday", "host": "pjtpartners.wd1.myworkdayjobs.com", "tenant": "pjtpartners", "site": "Careers"},
        {"company": "Guggenheim Securities", "type": "workday", "host": "guggenheim.wd1.myworkdayjobs.com", "tenant": "guggenheim", "site": "Guggenheim_Careers_Campus"},
        {"company": "Wellington Management", "label": "Wellington Management (campus)", "type": "workday", "host": "wellington.wd5.myworkdayjobs.com", "tenant": "wellington", "site": "Campus"},
        {"company": "Wellington Management", "label": "Wellington Management (external)", "type": "workday", "host": "wellington.wd5.myworkdayjobs.com", "tenant": "wellington", "site": "External"},
        {"company": "T. Rowe Price", "type": "workday", "host": "troweprice.wd5.myworkdayjobs.com", "tenant": "troweprice", "site": "TRowePriceInternational"},
        {"company": "Carlyle", "type": "workday", "host": "carlyle.wd1.myworkdayjobs.com", "tenant": "carlyle", "site": "Carlyle"},
        {"company": "Apollo", "type": "workday", "host": "athene.wd5.myworkdayjobs.com", "tenant": "athene", "site": "Apollo_Careers"},
        {"company": "ICG", "type": "workday", "host": "icg.wd3.myworkdayjobs.com", "tenant": "icg", "site": "external_careers"},
        {"company": "LSEG", "label": "LSEG (graduates & interns)", "type": "workday", "host": "lseg.wd3.myworkdayjobs.com", "tenant": "lseg", "site": "Graduate_Careers"},
        {"company": "RBC Capital Markets", "label": "RBC (early talent)", "type": "workday", "host": "rbc.wd3.myworkdayjobs.com", "tenant": "rbc", "site": "RBCEARLYTALENT1"},
        {"company": "Wells Fargo", "type": "workday", "host": "wf.wd1.myworkdayjobs.com", "tenant": "wf", "site": "WellsFargoJobs"},
        {"company": "Invesco", "type": "workday", "host": "invesco.wd1.myworkdayjobs.com", "tenant": "invesco", "site": "IVZ"},
        {"company": "abrdn", "type": "workday", "host": "abrdn.wd3.myworkdayjobs.com", "tenant": "abrdn", "site": "abrdn"},
        {"company": "Lincoln International", "type": "greenhouse", "board": "lincolninternational"},
        {"company": "Man Group", "type": "greenhouse", "board": "mangroup"},
        {"company": "Schonfeld", "type": "greenhouse", "board": "schonfeld"},
        {"company": "Marshall Wace", "type": "greenhouse", "board": "mwinternshipprogram"},
        {"company": "EQT", "type": "greenhouse", "board": "eqtpartners"},
        {"company": "Warburg Pincus", "type": "greenhouse", "board": "warburgpincusllc"},
        {"company": "Raine", "type": "lever", "account": "raine"},
        {"company": "Millennium", "type": "eightfold", "host": "mlp.eightfold.ai", "domain": "mlp.com"},
        {"company": "Capula Investment Management", "type": "workable", "account": "capula-investment-management-ltd"},
        {"company": "Marex", "type": "html", "url": "https://marex.breezy.hr/", "link_regex": "/p/[0-9a-f]{10,}-[a-z0-9-]+"},
        {"company": "StoneX", "type": "html", "url": "https://uk-stonex.icims.com/jobs/search?ss=1&in_iframe=1", "link_regex": "/jobs/\\d+/[^/\"]+/job", "default_location": "London, United Kingdom"},
        {"company": "RWE Supply & Trading", "type": "html", "urls": ["https://jobs.rwe.com/RWE/search/?q=&locationsearch=London", "https://jobs.rwe.com/RWE/search/?q=placement", "https://jobs.rwe.com/RWE/search/?q=intern&locationsearch=Singapore"], "link_regex": "/RWE/job/[^\"]+/\\d+/?"},
        {"company": "Mizuho", "label": "Mizuho (EMEA internships)", "type": "html", "url": "https://www.mizuhogroup.com/emea/careers/internship-programme/internship-roles", "link_regex": "grb\\.uk\\.com/internships/mizuho-[a-z0-9-]+", "default_location": "London, United Kingdom"},
        {"company": "Nomura", "type": "html", "urls": ["https://careers.nomura.com/Nomura/search/?q=intern&locationsearch=London", "https://careers.nomura.com/Nomura/search/?q=intern&locationsearch=Singapore", "https://careers.nomura.com/Nomura/search/?q=analyst&locationsearch=London"], "link_regex": "/Nomura/job/[^\"]+/\\d+/?"},
        {"company": "Nomura", "type": "html", "url": "https://nomuracampus.tal.net/vx/lang-en-GB/mobile-0/appcentre-ext/brand-4/xf-3348347fc789/candidate/jobboard/vacancy/1/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+", "label": "Nomura (campus)"},
        {"company": "Moelis", "type": "html", "url": "https://moelis-careers.tal.net/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/candidate/jobboard/vacancy/1/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+"},
        {"company": "BNP Paribas", "type": "html", "urls": ["https://group.bnpparibas/en/careers/all-job-offers/trainee-internship", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=2", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=3", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=4", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=5", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=6", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=7", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=8", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=9", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=10", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=11", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=12", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=13", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=14", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=15", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=16", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=17", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=18", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=19", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=20", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=21", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=22", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=23", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=24", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=25", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=26", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=27", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=28", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=29", "https://group.bnpparibas/en/careers/all-job-offers/trainee-internship?page=30", "https://group.bnpparibas/en/careers/all-job-offers/graduate-programme", "https://group.bnpparibas/en/careers/all-job-offers/graduate-programme?page=2", "https://group.bnpparibas/en/careers/all-job-offers/graduate-programme?page=3"], "link_regex": "/en/careers/job-offer/[a-z0-9-]+"},
        {"company": "Vitol", "type": "html", "url": "https://www.vitol.com/open-roles/", "link_regex": "jobs\\.smartrecruiters\\.com/Vitol/\\d+-[a-z0-9-]+"},
        {"company": "Louis Dreyfus Company", "type": "html", "url": "https://www.ldc.com/careers/join-ldc/", "link_regex": "/careers/join-ldc/job-details/(?:\\?id=[0-9a-f-]+|[a-z0-9-]+/)"},
        {"company": "G-Research", "type": "html", "url": "https://www.gresearch.com/join-us/", "link_regex": "/vacancies/[a-z0-9-]+/?$", "default_location": "London, United Kingdom"},
        {"company": "M&G", "type": "workday", "host": "mgpru.wd3.myworkdayjobs.com", "tenant": "mgpru", "site": "mandgprudential"},
        {"company": "Ares", "type": "workday", "host": "aresmgmt.wd1.myworkdayjobs.com", "tenant": "aresmgmt", "site": "External"},
        {"company": "Neuberger Berman", "type": "workday", "host": "nb.wd1.myworkdayjobs.com", "tenant": "nb", "site": "NBCareers"},
        {"company": "Northern Trust", "type": "workday", "host": "ntrs.wd1.myworkdayjobs.com", "tenant": "ntrs", "site": "ntcampus"},
        {"company": "TD Securities", "type": "workday", "host": "td.wd3.myworkdayjobs.com", "tenant": "td", "site": "TD_Bank_Careers"},
        {"company": "CIBC", "type": "workday", "host": "cibc.wd3.myworkdayjobs.com", "tenant": "cibc", "site": "campus"},
        {"company": "State Street", "type": "workday", "host": "statestreet.wd1.myworkdayjobs.com", "tenant": "statestreet", "site": "Global"},
        {"company": "CME Group", "type": "workday", "host": "cmegroup.wd1.myworkdayjobs.com", "tenant": "cmegroup", "site": "cme_careers"},
        {"company": "DRW", "type": "greenhouse", "board": "drweng"},
        {"company": "Hudson River Trading", "type": "greenhouse", "board": "wehrtyou"},
        {"company": "Squarepoint", "type": "greenhouse", "board": "squarepointcapital"},
        {"company": "Jump Trading", "type": "greenhouse", "board": "jumptrading"},
        {"company": "IMC", "type": "greenhouse", "board": "imc"},
        {"company": "Bridgewater", "type": "greenhouse", "board": "bridgewater89"},
        {"company": "Flow Traders", "type": "greenhouse", "board": "flowtraders"},
        {"company": "UOB", "type": "workday", "host": "uobgroup.wd3.myworkdayjobs.com", "tenant": "uobgroup", "site": "UOBExternal"},
        {"company": "Centrica", "type": "html", "urls": ["https://www.lifeatcentrica.com/jobs/", "https://www.lifeatcentrica.com/jobs?page=2", "https://www.lifeatcentrica.com/jobs?page=3"], "link_regex": "/jobs/r\\d+/[a-z0-9-]+/?"},
        {"company": "Peel Hunt", "type": "html", "url": "https://careersat.peelhunt.com/jobs", "link_regex": "/jobs/\\d+-[a-z0-9-]+", "default_location": "London, United Kingdom"},
        {"company": "Perella Weinberg", "type": "html", "url": "https://pwpcareers.tal.net/vx/lang-en-GB/mobile-0/appcentre-1/brand-4/candidate/jobboard/vacancy/1/adv/", "link_regex": "/candidate/so/pm/\\d+/pl/\\d+/opp/\\d+", "label": "Perella Weinberg (campus)"},
        {"company": "Perella Weinberg", "type": "workday", "host": "pwp.wd1.myworkdayjobs.com", "tenant": "pwp", "site": "PWP_Experienced_Opportunities", "label": "Perella Weinberg (Workday)"},
        {"company": "AllianceBernstein", "type": "workday", "host": "abglobal.wd1.myworkdayjobs.com", "tenant": "abglobal", "site": "alliancebernsteincareers"},
        {"company": "3i", "type": "workday", "host": "3i.wd103.myworkdayjobs.com", "tenant": "3i", "site": "Intern_Career"},
        {"company": "Oaktree", "type": "workday", "host": "oaktree.wd1.myworkdayjobs.com", "tenant": "oaktree", "site": "Oaktree"},
        {"company": "Zurich Insurance", "type": "html", "urls": ["https://www.careers.zurich.com/search/?q=intern&locationsearch=Zurich", "https://www.careers.zurich.com/search/?q=praktikum&locationsearch=Zurich", "https://www.careers.zurich.com/search/?q=intern&locationsearch=London"], "link_regex": "/job/[^\"]+/\\d+/?"},
        {"company": "ExxonMobil", "type": "html", "urls": ["https://jobs.exxonmobil.com/ExxonMobil/search/?q=intern&locationsearch=Singapore", "https://jobs.exxonmobil.com/ExxonMobil/search/?q=intern&locationsearch=London"], "link_regex": "/ExxonMobil/job/[^\"]+/\\d+/?"},
        {"company": "Chevron", "type": "workday", "host": "chevron.wd5.myworkdayjobs.com", "tenant": "chevron", "site": "University"},
        {"company": "Kpler", "type": "lever", "account": "kpler"},
        {"company": "General Atlantic", "type": "greenhouse", "board": "generalatlantic"},
        {"company": "HPS Investment Partners", "type": "greenhouse", "board": "hpsinvestmentpartners"},
        {"company": "Blue Owl", "type": "workday", "host": "blueowl.wd1.myworkdayjobs.com", "tenant": "blueowl", "site": "blueowl"},
        {"company": "Alpiq", "type": "html", "url": "https://www.alpiq.com/career/open-jobs", "link_regex": "/career/open-jobs/your-application/\\d+"},
        {"company": "Lloyds Banking Group", "type": "workday", "host": "lbg.wd3.myworkdayjobs.com", "tenant": "lbg", "site": "Undergraduate_careers"},
        {"company": "Columbia Threadneedle", "type": "workday", "host": "ameriprise.wd5.myworkdayjobs.com", "tenant": "ameriprise", "site": "Ameriprise"},
        {"company": "Nuveen", "type": "workday", "host": "tiaa.wd1.myworkdayjobs.com", "tenant": "tiaa", "site": "Search"},
        {"company": "Vanguard", "type": "workday", "host": "vanguard.wd5.myworkdayjobs.com", "tenant": "vanguard", "site": "vanguard_external"},
        {"company": "Cboe", "type": "workday", "host": "cboe.wd1.myworkdayjobs.com", "tenant": "cboe", "site": "External_Career_CBOE"},
        {"company": "Legal & General (LGIM)", "type": "html", "url": "https://careers.legalandgeneral.com/investment-jobs", "link_regex": "/job/[a-z0-9-]+-jid-\\d+"},  # v9
        {"company": "Janus Henderson", "type": "html", "url": "https://jobs.janushenderson.com/search?q=&sortColumn=referencedate&sortDirection=desc", "link_regex": "/job/[^\"/]+/\\d+/"},  # v9
        {"company": "Scotiabank", "type": "html", "url": "https://jobs.scotiabank.com/go/Student-&-New-Grad-Jobs/2298417/", "link_regex": "/job/[^\"/]+/\\d+/"},  # v9
        {"company": "Permira", "type": "greenhouse", "board": "permiraexternalprivate", "eu": True},  # v9
        {"company": "Atomico", "type": "greenhouse", "board": "atomico"},  # v9
        {"company": "CVC Credit Partners", "type": "workable", "account": "cvc-credit-partners"},  # v9
        {"company": "Balderton Capital", "type": "workable", "account": "baldertoncapital"},  # v9
        {"company": "DV Trading", "type": "greenhouse", "board": "dvtrading"},  # v9
        {"company": "Glencore UK (early careers)", "type": "greenhouse", "board": "glencoreuk", "eu": True},  # v9
        {"company": "Sixth Street", "type": "workday", "host": "sixthstreet.wd1.myworkdayjobs.com", "tenant": "sixthstreet", "site": "sixthstreetcareers"},  # v9
        {"company": "Verition Fund Management", "type": "greenhouse", "board": "veritiongroupllcinternships"},  # v9
        {"company": "LionTree", "type": "greenhouse", "board": "liontree"},  # v9
        {"company": "Rothesay", "type": "greenhouse", "board": "rothesaygraduates"},  # v9
        {"company": "Capstone Investment Advisors", "type": "greenhouse", "board": "capstoneinvestmentadvisors"},  # v9
        {"company": "Harrison Street", "type": "lever", "account": "harrisonst"},  # v9
        {"company": "Graham Capital Management", "type": "greenhouse", "board": "grahamcapitalmanagement"},  # v9
        {"company": "Howden Capital Markets & Advisory (Hyperion Group)", "type": "workday", "host": "hyperiongrp.wd3.myworkdayjobs.com", "tenant": "hyperiongrp", "site": "Hyperion_External"},  # v9
        {"company": "Maven Securities", "type": "greenhouse", "board": "emergingtalent"},  # v9
        {"company": "Motion Ventures", "type": "greenhouse", "board": "motionventures", "eu": True},  # v9
        {"company": "Davy (Bank of Ireland group)", "type": "workable", "account": "davy"},  # v9
        {"company": "Mirabaud", "type": "html", "url": "https://www.mirabaud.com/fr/carrieres/offres-demploi", "link_regex": "/fr/carrieres/offres-demploi/job-details/\\d+"},  # v9
        {"company": "StepStone Group", "type": "greenhouse", "board": "stepstone"},  # v9 (sondage API)
        {"company": "Jane Street", "type": "greenhouse", "board": "janestreet"},  # v9 (sondage API)
        {"company": "Qube Research & Technologies", "type": "greenhouse", "board": "quberesearchandtechnologies"},  # v9 (sondage API)
        {"company": "William Blair", "type": "greenhouse", "board": "williamblair"},  # v9 (sondage API)
        {"company": "AQR", "type": "greenhouse", "board": "aqr"},  # v9 (sondage API)
        {"company": "Winton", "type": "greenhouse", "board": "winton"},  # v9 (sondage API)
        {"company": "Canaccord Genuity", "type": "workday", "host": "cgf.wd10.myworkdayjobs.com", "tenant": "cgf", "site": "CG"},  # v10
        {"company": "Hayfin Capital Management", "type": "workable", "account": "hayfin-capital-management"},  # v10
        {"company": "Aviva Investors", "type": "workday", "host": "aviva.wd1.myworkdayjobs.com", "tenant": "aviva", "site": "Aviva_Investors_External"},  # v10
        {"company": "Octopus Group", "type": "html", "url": "https://octopusgroup.com/careers/listings", "link_regex": "/careers/listings/(?!page/)[a-z0-9-]+/?$"},  # v10
        {"company": "Berenberg", "type": "html", "url": "https://careers.berenberg.com/search-our-jobs?dept=Internships", "link_regex": "/search-our-jobs/[A-Za-z0-9-]+-\\d+-[A-Za-z-]+$"},  # v10
        {"company": "Cavendish", "type": "html", "url": "https://www.cavendish.com/category/current-roles/", "link_regex": "cavendish\\.com/(?!category/|people/|tag/|page/|wp-)[a-z0-9-]+/?$"},  # v10
        {"company": "Clarksons", "type": "html", "url": "https://careers.clarksons.com/Clarksons/go/View-All-Jobs/3979701/", "link_regex": "/Clarksons/job/[^\"]+/\\d+"},  # v10
        {"company": "Dymon Asia Capital", "type": "html", "url": "https://www.dymonasia.com/join-us/", "link_regex": "https://dymon\\.careers\\.hibob\\.com/jobs/[0-9a-f-]{36}", "default_location": "Singapore"},  # v10
    ],
    # Portail officiel de l'emploi à Singapour (offres « Internship/Attachment »)
    "mcf": {
        "enabled": True,
        "limit": 100,
        "max_pages": 2,
        "queries": ["intern", "internship", "summer intern", "investment", "trading", "commodities", "analyst",
                    "private equity", "venture capital", "M&A", "investment banking", "asset management",
                    "portfolio", "sales", "markets", "energy"],
    },
    "filters": {
        "max_age_days": 200,  # programmes de stage publiés tôt et ouverts des mois : on ne les écarte pas
        "extra_include": [],
        "extra_exclude": [],
        "include_summer": True,
    },
    "notifications": {
        "max_individual": 5,
        "open_dashboard_on_start": True,
        "digest_hour": 8,
    },
    # Entreprises prioritaires par défaut (modifiables depuis le site, enregistrées dans data/prioritaires.json)
    "priority_companies": ["Morgan Stanley", "Goldman Sachs", "J.P. Morgan", "Lazard", "Rothschild",
                           "BNP Paribas", "Bank of America", "Société Générale"],
    "closed_checks_per_run": 20,
    "parallel_sources": 12,
    "collect_budget_seconds": 400,  # au-delà, les sources pas encore lues passent au passage suivant (en priorité)
    "location_checks_per_run": 60,
    "date_checks_per_run": 40,  # offres sans date de publication : date lue sur la page de l'offre  # offres de sites carrières sans lieu : lecture du lieu sur la page de l'offre
    # Agrégateurs à API officielle : The Muse (sans clé), Adzuna et Reed (clés gratuites dans les secrets GitHub)
    "muse": {"enabled": True, "max_pages": 15,
             "locations": ["London, United Kingdom", "Paris, France", "Zurich, Switzerland", "Geneva, Switzerland",
                           "Singapore, Singapore", "Dublin, Ireland"]},
    "adzuna": {"enabled": True, "every_minutes": 240, "max_days_old": 3},
    "reed": {"enabled": True, "every_minutes": 60, "max_pages": 2},
    "description_checks_per_run": 40,  # descriptions lues avant de notifier (offres hors LinkedIn)
    "verify_checks_per_run": 30,       # offres déjà affichées recontrôlées par passage (hors LinkedIn)
    "verify_linkedin_per_run": 8,      # idem pour LinkedIn  # sites interrogés en même temps (un seul fil par site web)
    "cloud": {
        "ntfy_topic": "",
        "dashboard_url": "",
    },
}

# Fonctions remplacées en mode --cloud (notifications ntfy, lien public du tableau de bord)
SEND = notify.notify


def dash_link():
    return dashboard.file_url(DASH_PATH)


# ----------------------------------------------------------------------------- utilitaires
def log(msg):
    line = "[%s] %s" % (datetime.now().strftime("%d/%m %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if os.path.getsize(LOG_PATH) > 2_000_000:  # rotation simple
            os.replace(LOG_PATH, LOG_PATH + ".old")
    except Exception:
        pass


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        return copy.deepcopy(DEFAULT_CONFIG)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        try:
            user = json.load(f)
        except json.JSONDecodeError as e:
            sys.exit("config.json invalide (ligne %d) : %s\nCorrige le fichier ou supprime-le pour le régénérer."
                     % (e.lineno, e.msg))
    return _merge(DEFAULT_CONFIG, user)


def too_old(posted, cfg):
    """Vrai si la date de publication (AAAA-MM-JJ) dépasse filters.max_age_days."""
    if not posted:
        return False
    try:
        d = datetime.strptime(posted[:10], "%Y-%m-%d")
    except ValueError:
        return False
    return (datetime.now() - d).days > int(cfg["filters"].get("max_age_days", 30))


def _compact(s):
    return re.sub(r"[^a-z0-9]", "", filters.normalize(s))


def priority_list(cfg):
    """Liste des entreprises prioritaires : celle du site si elle existe, sinon celle de config.json."""
    try:
        with open(PRIORITY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        lst = data.get("companies") if isinstance(data, dict) else data
        if isinstance(lst, list):
            return [str(x) for x in lst if str(x).strip()]
    except (OSError, ValueError):
        pass
    return list(cfg.get("priority_companies") or [])


def is_priority(company, plist):
    c = _compact(company)
    return bool(c) and any(len(_compact(p)) >= 2 and _compact(p) in c for p in plist)


def paris_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:  # pas de base de fuseaux : heure d'été de Paris
        from datetime import timedelta, timezone
        return datetime.now(timezone(timedelta(hours=2)))


def workday_maintenance(now=None):
    """Fenêtre de maintenance hebdomadaire de Workday : samedi 06:00 à 11:00 UTC (marge incluse, heure d'été et d'hiver)."""
    d = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc)
    return d.weekday() == 5 and 6 <= d.hour < 11


# ----------------------------------------------------------------------------- collecte
class Tracker:
    def __init__(self, cfg, store):
        self.cfg = cfg
        self.store = store
        self.li_blocked = False  # LinkedIn a limité ce passage : pas d'autres requêtes LinkedIn jusqu'au suivant
        self.backoff = {}      # source -> timestamp avant lequel on ne réessaie pas
        self.backoff_len = {}  # source -> durée actuelle du backoff (s)
        store.set_meta("backoff:LinkedIn", 0)  # plus de pause LinkedIn entre les passages (voir _linkedin_finish)
        for name in ("LinkedIn", "Welcome to the Jungle", "Sites carrières Workday"):
            try:
                self.backoff[name] = float(store.get_meta("backoff:" + name, 0))
                self.backoff_len[name] = float(store.get_meta("backoff_len:" + name, 0)) or None
                if not self.backoff_len[name]:
                    self.backoff_len.pop(name)
            except ValueError:
                pass
        if store.get_meta("pause_reset_v9", "") != "1":
            # La maintenance Workday du 24/10 avait mis tous les sites Workday en pause 24 h : on lève ces pauses
            store.reset_site_pauses()
            store.set_meta("pause_reset_v9", "1")
        self._check_filter_version()
        self._init_region_seeding()

    # Zone ajoutée à une base déjà en service : pendant REGION_SEED_HOURS, les offres déjà en ligne de cette zone
    # entrent dans le tableau de bord sans notification (comme au tout premier passage), une seule annonce est envoyée.
    REGION_SEED_HOURS = 3

    def _init_region_seeding(self):
        now = time.time()
        self.region_seed_until, self.regions_announce, self.region_seeded = {}, [], {}
        in_service = self.store.db.execute("SELECT 1 FROM meta WHERE key LIKE 'seeded:%' LIMIT 1").fetchone()
        for reg in filters.REGION_NAMES[1:]:
            since = self.store.get_meta("region_since:" + reg)
            if since is None:
                since = now if in_service else 0  # base neuve : le premier passage normal suffit
                self.store.set_meta("region_since:" + reg, since)
                if in_service:
                    self.store.set_meta("region_announce:" + reg, "pending")
            since = float(since or 0)
            if since and now < since + self.REGION_SEED_HOURS * 3600:
                self.region_seed_until[reg] = since + self.REGION_SEED_HOURS * 3600
            elif self.store.get_meta("region_announce:" + reg) == "pending":
                self.regions_announce.append(reg)  # fenêtre silencieuse terminée : on annonce le total

    def _check_filter_version(self):
        """Après un changement des règles de filtrage, les offres déjà écartées sont réexaminées."""
        cur = str(filters.FILTER_VERSION)
        if self.store.get_meta("filter_version") != cur:
            n = self.store.purge_rejected()
            self.store.set_meta("filter_version", cur)
            if n:
                log("Règles de filtrage mises à jour : %d offres écartées seront réexaminées." % n)
            merged = self.migrate_site_keys()
            if merged:
                log("%d doublon(s) de sites carrières (adresses à jeton de session) supprimé(s)." % merged)
            self.refilter_offers()
            try:
                self.store.db.execute("VACUUM")  # la base est versionnée dans GitHub : on la garde compacte
            except Exception:
                pass

    def migrate_site_keys(self):
        """Offres de sites carrières enregistrées avec une adresse à jeton de session (tal.net : /xf-.../) : on passe à
        l'identifiant stable et on supprime les copies de la même offre créées à chaque passage."""
        db, removed = self.store.db, 0
        rows = [dict(r) for r in db.execute("SELECT uid, company, url, duplicate_of, first_seen FROM offers "
                                            "WHERE source='Site carrière' ORDER BY first_seen")]
        for o in rows:
            prefix = "Site carrière:%s:" % o["company"]
            if not o["uid"].startswith(prefix) or not o["uid"][len(prefix):].startswith("http"):
                continue
            new_uid = prefix + sources.stable_job_key(o["uid"][len(prefix):])
            if new_uid == o["uid"]:
                continue
            if db.execute("SELECT 1 FROM offers WHERE uid=?", (new_uid,)).fetchone():
                # copie plus récente de la même offre : supprimée, ses doublons rattachés à l'offre gardée
                db.execute("UPDATE offers SET duplicate_of=? WHERE duplicate_of=?", (new_uid, o["uid"]))
                db.execute("DELETE FROM offers WHERE uid=?", (o["uid"],))
                removed += 1
            else:
                db.execute("UPDATE offers SET uid=?, ext_id=? WHERE uid=?",
                           (new_uid, new_uid[len("Site carrière:"):], o["uid"]))
                db.execute("UPDATE offers SET duplicate_of=? WHERE duplicate_of=?", (new_uid, o["uid"]))
        # une offre rattachée à elle-même après fusion redevient principale
        db.execute("UPDATE offers SET duplicate_of=NULL WHERE duplicate_of=uid")
        db.commit()
        return removed

    def refilter_offers(self):
        """Les offres déjà retenues repassent dans le filtre (par l'intitulé) ; celles qui n'y répondent plus sont
        retirées du tableau et rangées dans les offres écartées. Leur description sera aussi recontrôlée."""
        removed = 0
        for o in self.store.offers():
            if o.get("closed"):
                continue
            r = self._classify(o)
            if r["region"] is None or r["category"] is None or r["intern"] == "no":
                removed += self.store.exclude_offer(o["uid"], r["reason"] or "hors périmètre")
        self.store.db.execute("UPDATE offers SET desc_checked=0")
        self.store.db.commit()
        if removed:
            log("Nouvelles règles : %d offre(s) déjà affichée(s) retirée(s) du tableau." % removed)
        return removed

    def _save_backoff(self, name):
        self.store.set_meta("backoff:" + name, self.backoff.get(name, 0))
        self.store.set_meta("backoff_len:" + name, self.backoff_len.get(name, 0))

    def _classify(self, j, description="", employment_type=""):
        f = self.cfg["filters"]
        r = filters.classify(j["title"], j.get("location", ""), description,
                             employment_type or j.get("employment_type", ""),
                             f.get("extra_include"), f.get("extra_exclude"), company=j.get("company") or "")
        # include_summer ne concerne que la France : en Suisse et à Singapour, summer et off-cycle sont gardés
        if r["ok"] and r["summer"] and not f.get("include_summer", True) and r.get("region") == "France":
            r["ok"], r["reason"] = False, "summer exclu (config)"
        return r

    def _run_source(self, name, fn):
        if not self._source_ready(name):
            return []
        try:
            res = fn()
        except Exception as e:  # noqa: BLE001
            return self._source_done(name, error=e)
        return self._source_done(name, res)

    def _source_ready(self, name):
        """Vrai si la source peut être interrogée maintenant (pas de pause en cours)."""
        now = time.time()
        if name not in self.backoff:
            try:
                self.backoff[name] = float(self.store.get_meta("backoff:" + name, 0))
                bl = float(self.store.get_meta("backoff_len:" + name, 0))
                if bl:
                    self.backoff_len[name] = bl
            except ValueError:
                pass
        if self.backoff.get(name, 0) > now:
            mins = int((self.backoff[name] - now) / 60) + 1
            if int(self.store.get_meta("fails:" + name, 0) or 0) >= 6:
                return False  # le message "non lisible" reste affiché tel quel
            self.store.set_source(name, False, "En pause %d min (limitation du site)" % mins)
            return False
        return True

    def _source_done(self, name, res=None, error=None):
        """Enregistre le résultat (ou l'erreur) d'une source et renvoie les offres lues."""
        now = time.time()
        try:
            if error is not None:
                raise error
            errs = []
            if isinstance(res, tuple):
                res, errs = res
            if self.backoff_len.pop(name, None):
                self._save_backoff(name)
            if self.store.get_meta("fails:" + name, "0") != "0":
                self.store.set_meta("fails:" + name, 0)
            msg = "OK : %d offres analysées" % len(res)
            if errs:
                msg += " · erreurs : " + "; ".join(errs)
            self.store.set_source(name, not (errs and not res), msg, len(res))
            return res
        except sources.RateLimited as e:
            if name == "LinkedIn":
                log("LinkedIn : limité dès la première requête (%s), nouvel essai au prochain passage" % e)
                self.store.set_source(name, False, "Limité par LinkedIn sur ce passage, nouvel essai au suivant")
                return []
            d = min(max(self.backoff_len.get(name, 600) * 2, 900), 7200)
            self.backoff_len[name] = d
            self.backoff[name] = now + d
            self._save_backoff(name)
            log("%s : limité par le site (%s), pause de %d min" % (name, e, d // 60))
            self.store.set_source(name, False, "Limité par le site, pause %d min" % (d // 60))
        except sources.Unavailable as e:
            # Maintenance ou panne passagère : aucune pause, nouvel essai dès le passage suivant
            log("%s : indisponible sur ce passage (%s)" % (name, e))
            self.store.set_source(name, False, "Indisponible sur ce passage (%s), nouvel essai au suivant" % str(e)[:150])
        except Exception as e:
            fails = int(self.store.get_meta("fails:" + name, 0) or 0) + 1
            self.store.set_meta("fails:" + name, fails)
            if name.startswith("Site · ") and fails >= 6:
                # Un site qui a fonctionné ces 3 derniers jours n'est mis en pause qu'une heure (panne passagère) ;
                # un site illisible de façon durable n'est réessayé qu'une fois par jour.
                recent = now - self.store.source_last_ok(name) < 3 * 86400
                pause = 3600 if recent else 86400
                self.backoff[name] = now + pause
                self.backoff_len[name] = pause
                self._save_backoff(name)
                log("%s : illisible après %d essais, nouvel essai dans %s (%s)" % (name, fails, "1 h" if recent else "24 h", e))
                self.store.set_source(name, False, ("Panne passagère, nouvel essai dans 1 h. " if recent else
                                                    "Non lisible automatiquement, nouvel essai dans 24 h. ")
                                      + "Détail : %s" % str(e)[:120])
            else:
                log("%s : ERREUR %s" % (name, e))
                self.store.set_source(name, False, "Erreur : %s" % str(e)[:200])
        return []

    def _site_prepare(self, site):
        """Copie de la config du site, avec l'adresse corrigée trouvée lors d'un passage précédent."""
        s = dict(site)
        key = "found:" + site.get("label", site["company"])
        try:
            found = json.loads(self.store.get_meta(key, "{}") or "{}")
        except ValueError:
            found = {}
        if found.get("site_ref") == [site.get("host"), site.get("site")]:
            s.update(_host=found["host"], _site=found["site"], _discovered=True)
        return s

    def _site_finish(self, site, s):
        if s.get("_discovered") and s.get("_host"):
            key = "found:" + site.get("label", site["company"])
            self.store.set_meta(key, json.dumps({"site_ref": [site.get("host"), site.get("site")],
                                                 "host": s["_host"], "site": s["_site"]}))

    def _run_site(self, site, fn):
        """Lance un site en réutilisant l'adresse corrigée trouvée lors d'un passage précédent."""
        s = self._site_prepare(site)
        res = fn(s)
        self._site_finish(site, s)
        return res

    def _collect_linkedin(self):
        state = {"offset": int(self.store.get_meta("li_offset", 0) or 0)}
        try:
            return sources.collect_linkedin(self.cfg, log, state)
        finally:
            self._linkedin_finish(state)

    def _linkedin_finish(self, state):
        # Pas de pause après une limitation : chaque passage GitHub tourne sur une machine (et une adresse IP)
        # différente, une pause ne ferait que sauter des passages qui auraient pu aboutir.
        self.store.set_meta("li_offset", state.get("offset", 0))
        if state.get("rate_limited"):
            self.li_blocked = True

    @staticmethod
    def _host_of(site):
        api = {"greenhouse": "boards-api.greenhouse.io", "lever": "api.lever.co", "ashby": "api.ashbyhq.com",
               "workable": "apply.workable.com"}.get(site.get("type"))
        if api:
            return api  # une seule file par API commune, pour rester discret
        if site.get("host"):
            return site["host"].split(".")[0] if "myworkdayjobs" in site["host"] else site["host"]
        u = site.get("url") or (site.get("urls") or [""])[0]
        return urllib.parse.urlparse(u).netloc or site.get("type", "") + ":" + site.get("company", "")

    def collect(self):
        """Interroge toutes les sources en parallèle (un seul fil par site web, pour rester discret)
        et renvoie les lots d'offres dans l'ordre de la configuration.

        La base SQLite n'est lue et écrite que dans le fil principal : les fils ne font que du réseau."""
        c = self.cfg
        tasks = []  # (nom, groupe, fonction réseau, fonction de fin ou None)
        if c["linkedin"]["enabled"]:
            st = {"offset": int(self.store.get_meta("li_offset", 0) or 0),
                  "known_ids": {r[0] for r in self.store.db.execute(
                      "SELECT ext_id FROM offers WHERE source='LinkedIn' UNION "
                      "SELECT substr(uid, 10) FROM rejected WHERE uid LIKE 'LinkedIn:%'")}}
            self._li_state = st
            tasks.append(("LinkedIn", "linkedin", lambda st=st: sources.collect_linkedin(c, log, st),
                          lambda st=st: self._linkedin_finish(st)))
        if c["wttj"]["enabled"]:
            tasks.append(("Welcome to the Jungle", "wttj", lambda: sources.collect_wttj(c, log), None))
        if c["workday"]["enabled"] and c["workday"]["tenants"]:
            tasks.append(("Sites carrières Workday", "workday-tenants", lambda: sources.collect_workday(c, log), None))
        if (c.get("mcf") or {}).get("enabled"):
            tasks.append(("MyCareersFuture", "mcf", lambda: sources.collect_mcf(c, log), None))
        if (c.get("muse") or {}).get("enabled"):
            tasks.append(("The Muse", "muse", lambda: sources.collect_muse(c, log), None))
        # API à quota (clés dans les secrets GitHub) : appelées moins souvent, seulement si la clé existe
        for name, key_env, fn, every in (("Adzuna", "ADZUNA_APP_KEY", sources.collect_adzuna, "adzuna"),
                                         ("Reed", "REED_API_KEY", sources.collect_reed, "reed")):
            conf = c.get(every) or {}
            if not conf.get("enabled") or not os.environ.get(key_env):
                continue
            last = float(self.store.get_meta("last_run:" + name, 0) or 0)
            if time.time() - last < float(conf.get("every_minutes", 240)) * 60 - 120:
                continue
            tasks.append((name, every, lambda fn=fn: fn(c, log),
                          lambda name=name: self.store.set_meta("last_run:" + name, time.time())))
        for site in c.get("sites") or []:
            fn = sources.SITE_COLLECTORS.get(site.get("type"))
            if not fn or not site.get("enabled", True):
                continue
            s = self._site_prepare(site)
            tasks.append(("Site · %s" % site.get("label", site["company"]), self._host_of(site),
                          lambda s=s, fn=fn: fn(s), lambda site=site, s=s: self._site_finish(site, s)))

        if workday_maintenance():
            # Maintenance hebdomadaire Workday (samedi 06:00 à 11:00 UTC) : on ne l'interroge pas, sans compter d'échec
            wd = {"Site · %s" % x.get("label", x["company"]) for x in c.get("sites") or [] if x.get("type") == "workday"}
            wd.add("Sites carrières Workday")
            for t in tasks:
                if t[0] in wd:
                    self.store.set_source(t[0], False, "Maintenance hebdomadaire Workday (samedi matin), reprise automatique")
            tasks = [t for t in tasks if t[0] not in wd]
        ready = [t for t in tasks if self._source_ready(t[0])]
        # Les sources interrogées il y a le plus longtemps passent en premier : si le budget de temps est atteint,
        # celles qui n'ont pas pu être lues seront prioritaires au passage suivant.
        last_run = {r[0]: r[1] or 0 for r in self.store.db.execute("SELECT name, last_run FROM source_status")}
        groups = {}
        for t in ready:
            groups.setdefault(t[1], []).append(t)
        for items in groups.values():
            items.sort(key=lambda t: last_run.get(t[0], 0))

        outcomes = {}
        t_start = time.time()
        deadline = t_start + float(c.get("collect_budget_seconds", 400))
        if getattr(self, "_li_state", None) is not None:
            self._li_state["deadline"] = deadline - 10  # LinkedIn s'arrête aussi à la fin du budget de temps

        def run_group(items):
            for name, _, net, _ in items:
                if time.time() > deadline:
                    outcomes[name] = ("skip", None, 0.0)
                    continue
                t0 = time.time()
                try:
                    outcomes[name] = (net(), None, time.time() - t0)
                except Exception as e:  # noqa: BLE001
                    outcomes[name] = (None, e, time.time() - t0)

        workers = max(1, int(c.get("parallel_sources", 6)))
        if workers == 1 or len(groups) <= 1:
            for items in groups.values():
                run_group(items)
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                # Les groupes les plus longs d'abord, pour que le passage se termine au plus tôt
                order = sorted(groups.values(), key=lambda it: (it[0][1] != "linkedin",
                                                                 min(last_run.get(t[0], 0) for t in it) > t_start - 3600,
                                                                 -len(it)))
                for f in [ex.submit(run_group, it) for it in order]:
                    f.result()

        batches, skipped = [], []
        for name, _, _, finish in tasks:
            if name not in outcomes or outcomes[name][0] == "skip":
                if name in outcomes:
                    skipped.append(name)
                batches.append((name, []))
                continue
            if finish:
                try:
                    finish()
                except Exception as e:  # noqa: BLE001
                    log("%s : %s" % (name, e))
            res, err, _ = outcomes[name]
            batches.append((name, self._source_done(name, res, error=err)))
        total = time.time() - t_start
        timings = sorted(((round(v[2], 1), k) for k, v in outcomes.items() if v[0] != "skip"), reverse=True)
        self.store.set_meta("collect_seconds", round(total, 1))
        self.store.set_meta("collect_timings", json.dumps(timings[:40], ensure_ascii=False))
        self.store.set_meta("collect_skipped", json.dumps(skipped, ensure_ascii=False))
        log("Collecte : %.0f s, %d sources lues, %d reportées au passage suivant (budget de temps)%s"
            % (total, len(outcomes) - len(skipped), len(skipped),
               " · plus lentes : " + ", ".join("%s %.0f s" % (k, v) for v, k in timings[:5]) if timings else ""))
        return batches

    def _accept(self, j, r, seed, new_list):
        seed = seed or self.store.in_seed(j["uid"])
        reg = r.get("region")
        if not seed and self.region_seed_until.get(reg, 0) > time.time():
            seed = True
            self.region_seeded[reg] = self.region_seeded.get(reg, 0) + 1
            self.store.set_meta("region_seeded:" + reg, int(self.store.get_meta("region_seeded:" + reg, 0) or 0) + 1)
        j["category"], j["summer"] = r["category"], r["summer"]
        j["dedup_key"] = filters.dedup_key(j.get("company"), j["title"], r.get("region") or "France")
        dup = self.store.find_duplicate(j["dedup_key"])
        notified = not seed and dup is None
        self.store.add_offer(j, notified=notified, duplicate_of=dup)
        if dup is None:
            log("  ✔ %s · %s · %s" % (j.get("company"), j["title"], j["category"]))
            if notified:
                new_list.append(j)

    def cycle(self):
        self.li_blocked = False  # nouvelle tentative LinkedIn à chaque passage
        new_list, seeded_now = [], []
        details_budget = self.cfg["linkedin"]["detail_limit_per_cycle"]
        detail_queue, desc_queue, loc_queue = [], [], []
        for name, jobs in self.collect():
            seed = self.store.get_meta("seeded:" + name) is None
            for j in jobs:
                j["uid"] = "%s:%s" % (j["source"], j["ext_id"])
                if self.store.known(j["uid"]):
                    continue
                if too_old(j.get("posted"), self.cfg):
                    self.store.add_rejected(j["uid"], "publiée il y a trop longtemps", j)
                    continue
                r = self._classify(j)
                if (not r["ok"] and r["region"] is None and j["source"] == "Site carrière"
                        and not (j.get("location") or "").strip()):
                    # Page liste sans lieu : si l'intitulé est dans le périmètre, le lieu est lu sur la page de l'offre
                    probe = self._classify(dict(j, location="Paris"))
                    if probe["ok"] or probe["intern"] == "unknown":
                        loc_queue.append((j, seed))
                        continue
                if j["source"] == "LinkedIn" and (r["ok"] or r["intern"] == "unknown"):
                    # On va chercher le lien carrière (et confirmer le stage si besoin)
                    detail_queue.append((0 if r["ok"] else 1, j, r, seed))
                elif r["ok"] and seed:
                    self._accept(j, r, seed, new_list)  # premier passage silencieux : description contrôlée ensuite
                elif r["ok"] or r["intern"] == "unknown":
                    # Avant de notifier : description lue (allemand/mandarin exigé ? vraiment un stage ?)
                    desc_queue.append((0 if r["ok"] else 1, j, r, seed))
                else:
                    self.store.add_rejected(j["uid"], r["reason"] or "?", j)
            if seed and jobs:
                seeded_now.append(name)

        self._check_locations(loc_queue, desc_queue, new_list)
        self._check_descriptions(desc_queue, new_list)

        # Offres LinkedIn retenues d'abord, puis celles à confirmer
        detail_queue.sort(key=lambda x: x[0])
        for i, (prio, j, r, seed) in enumerate(detail_queue):
            if details_budget <= 0 or self.li_blocked:
                if prio == 0:  # stage certain : on notifie avec le lien LinkedIn, sans attendre
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])  # existait déjà au 1er passage : pas de notification
                continue  # "à confirmer" : sera retenté au prochain passage
            details_budget -= 1
            try:
                d = sources.linkedin_detail(j["ext_id"])
                j["apply_url"] = d["apply_url"]
                r2 = self._classify(j, d["description"], d["employment_type"])
                if prio == 0 and r2["intern"] == "no" and filters.INTERN_TITLE.search(filters.normalize(j["title"])):
                    r2 = r  # le titre dit "stage" : on garde la décision initiale
                j["desc_checked"] = 1
                if r2["ok"]:
                    self._accept(j, r2, seed, new_list)
                else:
                    self.store.add_rejected(j["uid"], r2["reason"] or "?", j)
            except sources.RateLimited as e:
                self.li_blocked = True  # pour la suite de ce passage seulement
                log("LinkedIn (détails) : limité (%s), reprise dans 15 min" % e)
                if prio == 0:
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])
            except Exception as e:
                log("LinkedIn détail %s : %s" % (j["ext_id"], e))
                if prio == 0:
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])
            if i < len(detail_queue) - 1:
                time.sleep(random.uniform(1.5, 3.5))

        for name in seeded_now:
            self.store.set_meta("seeded:" + name, "1")
        self.store.prune()
        return new_list, seeded_now

    @staticmethod
    def _desc_employment(d):
        """Type de contrat utilisable : celui de LinkedIn / MyCareersFuture toujours, ailleurs seulement s'il dit "stage"
        (certains sites marquent "Full time" des stages à plein temps)."""
        emp = d.get("employment_type") or ""
        if d.get("trusted") or re.search(r"(?i)intern|stage|praktik|attachment", emp):
            return emp
        return ""

    def _check_locations(self, queue, desc_queue, new_list):
        """Offres de sites carrières sans lieu sur la page liste : lieu lu sur la page de l'offre (budget par passage).
        Au-delà du budget, l'offre n'est pas enregistrée et sera reprise au passage suivant."""
        budget = int(self.cfg.get("location_checks_per_run", 40))
        for j, seed in queue:
            if budget <= 0:
                continue
            budget -= 1
            try:
                loc = sources.fetch_location(j)
            except sources.RateLimited:
                budget = 0
                continue
            except Exception:  # noqa: BLE001
                loc = ""
            if not loc:
                self.store.add_rejected(j["uid"], "hors zone (lieu introuvable sur la page de l'offre)", j)
                continue
            j["location"] = loc
            r = self._classify(j)
            if r["ok"] and seed:
                self._accept(j, r, seed, new_list)
            elif r["ok"] or r["intern"] == "unknown":
                desc_queue.append((0 if r["ok"] else 1, j, r, seed))
            else:
                self.store.add_rejected(j["uid"], r["reason"] or "?", j)

    def _check_descriptions(self, queue, new_list):
        """Offres hors LinkedIn : lecture de la description avant de notifier, dans la limite d'un budget par passage.
        Au-delà : une offre déjà sûre est retenue (contrôlée au passage suivant), une offre à confirmer attend."""
        budget = int(self.cfg.get("description_checks_per_run", 40))
        queue.sort(key=lambda x: x[0])
        for prio, j, r, seed in queue:
            if budget <= 0:
                if prio == 0:
                    self._accept(j, r, seed, new_list)
                elif seed:
                    self.store.mark_seed(j["uid"])
                continue
            budget -= 1
            try:
                d = sources.fetch_description(j)
            except sources.RateLimited:
                d, budget = None, 0
            if d is None:
                if prio == 0:
                    j["desc_checked"] = 2  # description illisible automatiquement
                    self._accept(j, r, seed, new_list)
                else:
                    self.store.add_rejected(j["uid"], "stage à confirmer", j)
                continue
            r2 = self._classify(j, d["description"], self._desc_employment(d))
            if r2["ok"]:
                j["desc_checked"] = 1
                self._accept(j, r2, seed, new_list)
            else:
                self.store.add_rejected(j["uid"], r2["reason"] or "?", j)
            time.sleep(random.uniform(0.1, 0.4))

    def backfill_dates(self):
        """Offres sans date de publication (pages liste sans date) : date lue sur la page de l'offre, quelques-unes
        par passage, trois essais au plus par offre."""
        budget, found = int(self.cfg.get("date_checks_per_run", 40)), 0
        for o in self.store.offers_without_date():
            if budget <= 0:
                break
            key = "date_try:" + o["uid"]
            tries = int(self.store.get_meta(key, 0) or 0)
            if tries >= 3:
                continue
            budget -= 1
            try:
                d = sources.fetch_posted(o)
            except sources.RateLimited:
                break
            except Exception:  # noqa: BLE001
                d = ""
            if d:
                self.store.set_posted(o["uid"], d)
                found += 1
            else:
                self.store.set_meta(key, tries + 1)
        if found:
            log("Dates de publication retrouvées sur la page de l'offre : %d" % found)
        return found

    def verify_offers(self):
        """Contrôle progressif des offres déjà affichées : description lue (langue exigée, type de contrat).
        Une offre qui exige l'allemand ou le mandarin, ou qui n'est finalement pas un stage, est retirée du tableau."""
        budget = int(self.cfg.get("verify_checks_per_run", 30))
        li_budget = int(self.cfg.get("verify_linkedin_per_run", 8))
        todo = self.store.offers_to_verify()
        # D'abord les intitulés sans le mot "stage", puis la Suisse et Singapour, puis les plus récentes
        todo.sort(key=lambda o: (bool(filters.INTERN_TITLE.search(filters.normalize(o["title"]))),
                                 filters.region_of(o["location"], o["title"]) == "France", -(o["first_seen"] or 0)))
        removed = 0
        for o in todo:
            is_li = o["source"] == "LinkedIn"
            if is_li:
                if li_budget <= 0 or self.li_blocked:
                    continue
                li_budget -= 1
            else:
                if budget <= 0:
                    continue
                budget -= 1
            try:
                d = sources.fetch_description(o)
            except sources.RateLimited:
                if is_li:
                    self.li_blocked = True
                continue
            if d is None:
                self.store.set_desc_checked(o["uid"], 2)
                continue
            r = self._classify(o, d["description"], self._desc_employment(d))
            lang = (r["reason"] or "").startswith("langue requise")
            if lang or (r["intern"] == "no" and d.get("trusted")):
                removed += self.store.exclude_offer(o["uid"], r["reason"])
                log("  ✖ retirée : %s · %s (%s)" % (o["company"], o["title"], r["reason"]))
            else:
                self.store.set_desc_checked(o["uid"], 1)
            time.sleep(random.uniform(1.0, 2.0) if is_li else random.uniform(0.1, 0.4))
        return removed

    def notify_new(self, new_list):
        """Offres prioritaires : toujours une notification urgente chacune. Les autres : une par offre,
        ou une seule notification groupée au-delà de max_individual."""
        if not new_list:
            return
        plist = priority_list(self.cfg)
        prio = [j for j in new_list if is_priority(j.get("company"), plist)]
        rest = [j for j in new_list if not is_priority(j.get("company"), plist)]
        for j in prio:
            _send(SEND, "⭐ %s · %s" % (j.get("company") or "Entreprise prioritaire", j["category"]),
                  "%s\n📍 %s · %s" % (j["title"], place_label(j.get("location"), j["title"]), j["source"]),
                  j.get("apply_url") or j["url"], priority=5, tags=["star"],
                  extra=[("Voir dans le tableau", offer_link(j))])
            time.sleep(1)
        mx = self.cfg["notifications"]["max_individual"]
        if len(rest) <= mx:
            for j in rest:
                _send(SEND, "%s · %s" % (j.get("company") or "Nouvelle offre", j["category"]),
                      "%s\n📍 %s · %s" % (j["title"], place_label(j.get("location"), j["title"]), j["source"]),
                      j.get("apply_url") or j["url"], extra=[("Voir dans le tableau", offer_link(j))])
                time.sleep(1)
        else:
            counts = region_counts(rest)
            if len(counts) > 1:
                title = "%d nouvelles offres · %s" % (len(rest), ", ".join("%s %d" % kv for kv in counts))
            else:
                title = "%d nouvelles offres de stage %s" % (len(rest), REGION_IN.get(counts[0][0], "") if counts
                                                             else "")
            body = ", ".join(sorted({"%s (%s)" % (j.get("company") or "?",
                                                  filters.city_of(j.get("location"), j["title"]) or "?")
                                     for j in rest}))
            _send(SEND, title.strip(), body[:300], dash_link() + "#nouvelles", button="Voir les nouvelles offres")

    def announce_regions(self):
        """Une notification quand de nouvelles zones sont ajoutées à un tracker déjà en service."""
        if not self.regions_announce:
            return
        regs, self.regions_announce = self.regions_announce, []
        n = sum(int(self.store.get_meta("region_seeded:" + r, 0) or 0) for r in regs)
        for r in regs:
            self.store.set_meta("region_announce:" + r, "done")
        _send(SEND, "Nouvelles zones suivies : %s" % ", ".join(regs),
              "%d offre%s déjà en ligne ajoutée%s au tableau de bord sans notification. Désormais, chaque "
              "nouvelle offre de ces zones est notifiée avec sa localisation." % (n, "s" if n > 1 else "", "s" if n > 1 else ""),
              dash_link(), button="Voir le tableau", priority=3, tags=["earth_africa"])

    def check_closed(self):
        """Revérifie quelques offres par passage et marque celles qui ont été retirées."""
        n_closed, li_budget = 0, 8
        for o in self.store.offers_to_check(int(self.cfg.get("closed_checks_per_run", 20))):
            is_li = o["source"] == "LinkedIn"
            if is_li:
                if li_budget <= 0 or self.li_blocked:
                    continue
                li_budget -= 1
            try:
                res = sources.check_open(o)
            except sources.RateLimited:
                if is_li:
                    li_budget = 0
                continue
            if res is None:
                continue
            self.store.set_checked(o["uid"], closed=not res)
            if not res:
                n_closed += 1
                log("  ✖ fermée : %s · %s" % (o.get("company"), o["title"]))
            time.sleep(random.uniform(0.5, 1.5) if not is_li else random.uniform(1.5, 3))
        return n_closed

    def maybe_digest(self, now=None):
        """Récapitulatif quotidien (8 h, heure de Paris) des nouvelles offres des dernières 24 h."""
        now = now or paris_now()
        hour = int(self.cfg["notifications"].get("digest_hour", 8))
        today = now.strftime("%Y-%m-%d")
        if now.hour < hour or self.store.get_meta("digest_date") == today:
            return False
        self.store.set_meta("digest_date", today)
        recent = [o for o in self.store.recent_notified(time.time() - 86400) if not o.get("closed")]
        if not recent:
            _send(SEND, "Récap du matin", "Aucune nouvelle offre dans tes critères ces dernières 24 h.",
                  dash_link(), button="Voir le tableau", priority=2, tags=["sunrise"])
            return True
        counts = {}
        for o in recent:
            counts[o["category"]] = counts.get(o["category"], 0) + 1
        plist = priority_list(self.cfg)
        top = sorted(recent, key=lambda o: (not is_priority(o.get("company"), plist), -o["first_seen"]))[:5]
        lines = ["📍 " + " · ".join("%s %d" % kv for kv in region_counts(recent))]
        lines += [" · ".join("%s %d" % (k, v) for k, v in sorted(counts.items(), key=lambda x: -x[1]))]
        lines += ["%s%s · %s · %s" % ("⭐ " if is_priority(o.get("company"), plist) else "", o.get("company"), o["title"],
                                      filters.city_of(o.get("location"), o["title"]) or "?")
                  for o in top]
        if len(recent) > 5:
            lines.append("… et %d autres" % (len(recent) - 5))
        _send(SEND, "Récap du matin · %d nouvelle%s offre%s" % (len(recent), "s" if len(recent) > 1 else "",
                                                               "s" if len(recent) > 1 else ""),
              "\n".join(lines), dash_link() + "#nouvelles", button="Voir les nouvelles offres", priority=3,
              tags=["sunrise"])
        return True


REGION_IN = {"France": "à Paris", "Suisse": "en Suisse", "Singapour": "à Singapour", "Londres": "à Londres",
             "Dublin": "à Dublin"}


def place_label(location, title=""):
    """Lieu explicite pour les notifications : "Genève, Suisse", "Paris, France", "Singapour"."""
    reg = filters.region_of(location, title)
    if not reg:
        return location or "Lieu inconnu"
    city = filters.city_of(location, title)
    return reg if not city or city == reg else "%s, %s" % (city, reg)


def region_counts(offers):
    """[(zone, nombre)] dans l'ordre France, Suisse, Singapour, pour les zones présentes."""
    c = {}
    for o in offers:
        reg = filters.region_of(o.get("location"), o.get("title") or "") or "Autre"
        c[reg] = c.get(reg, 0) + 1
    order = list(filters.REGION_NAMES) + ["Autre"]
    return [(k, c[k]) for k in order if k in c]


def _send(fn, title, message, url=None, button="Postuler", priority=4, tags=None, extra=None):
    """Appelle la fonction de notification avec les options qu'elle accepte (ntfy en a plus que le bureau)."""
    import inspect
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        params = {}
    kw = {"button": button}
    for k, v in (("priority", priority), ("tags", tags), ("extra", extra)):
        if k in params:
            kw[k] = v
    return fn(title, message, url, **kw)


def offer_link(j):
    """Lien vers l'offre dans le tableau de bord (onglet de sa zone, carte mise en évidence)."""
    return dash_link() + "#o=" + urllib.parse.quote(j["uid"], safe="")


# ----------------------------------------------------------------------------- modes
def write_dashboard(store, cfg, next_run=None):
    offers = []
    for o in store.offers():
        raw = o.get("posted") or ""
        # Dates textuelles ("Posted 30+ Days Ago"...) : converties par rapport au jour de détection
        o["posted"] = sources.norm_posted(raw, datetime.fromtimestamp(o["first_seen"]).date())
        o["posted_plus"] = "+" in raw
        o["title"] = sources._text(o["title"])  # corrige les titres déjà enregistrés avec &amp;
        o["company"] = sources._text(o.get("company") or "")
        region = filters.region_of(o.get("location"), o["title"])
        if region is None:
            continue  # (pas de limite d'âge ici : une offre retenue reste affichée tant qu'elle est ouverte)
        o["region"], o["city"] = region, filters.city_of(o.get("location"), o["title"])
        # Même décision qu'à l'arrivée de l'offre (avec l'employeur) : une offre notifiée est toujours affichée
        cat, _ = filters.categorize(o["title"], o.get("company") or "")
        if cat is None and o["category"] != "Autre (mot-clé perso)":
            continue
        o["category"] = cat or o["category"]
        offers.append(o)
    keep = ("uid", "company", "title", "category", "location", "url", "apply_url", "posted", "posted_plus",
            "first_seen", "source", "summer", "closed", "closed_at", "region", "city", "notified")
    rows = []
    for o in offers:
        r = {k: o.get(k) for k in keep}
        r["closed"] = bool(o.get("closed"))
        r["summer"] = bool(o.get("summer"))
        r["notified"] = bool(o.get("notified"))
        others = store.other_links(o["uid"])
        # Autres sources de la même offre : une seule par source, jamais la source déjà affichée, 3 au plus
        links, seen_src = [], {o["source"]}
        for x in others:
            if x["source"] in seen_src:
                continue
            seen_src.add(x["source"])
            links.append({"source": x["source"], "url": x.get("apply_url") or x["url"]})
        if links:
            r["others"] = links[:3]
        rows.append(r)
    active = {"LinkedIn", "Welcome to the Jungle", "Sites carrières Workday"} | {
        "Site · %s" % x.get("label", x["company"]) for x in cfg.get("sites") or [] if x.get("enabled", True)} | (
        {"MyCareersFuture"} if (cfg.get("mcf") or {}).get("enabled") else set()) | (
        {"The Muse"} if (cfg.get("muse") or {}).get("enabled") else set()) | {
        n for n, k, e in (("Adzuna", "ADZUNA_APP_KEY", "adzuna"), ("Reed", "REED_API_KEY", "reed"))
        if (cfg.get(e) or {}).get("enabled") and os.environ.get(k)}
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    payload = {
        "generated": time.time(),
        "next_run": next_run,
        "interval": cfg["interval_minutes"],
        "offers": rows,
        "sources": [x for x in store.sources() if x["name"] in active],
        "priority": priority_list(cfg),
        "repo": repo if "/" in repo else None,
        "rejected": [dict(r, title=sources._text(r["title"]), company=sources._text(r.get("company") or ""),
                          region=filters.region_of(r.get("location"), r.get("title") or ""))
                     for r in store.recent_rejected(time.time() - 72 * 3600, 300)],
    }
    dashboard.write(DASH_PATH, payload)


def run_check(cfg):
    print("Diagnostic des sources (rien n'est enregistré)\n")
    print("Notifications : %s\n" % notify.backend_name())
    t = Tracker(cfg, Store(":memory:"))
    tests = []
    if cfg["linkedin"]["enabled"]:
        c2 = copy.deepcopy(cfg)
        c2["linkedin"]["queries"] = cfg["linkedin"]["queries"][:2]
        tests.append(("LinkedIn (2 requêtes)", lambda: sources.collect_linkedin(c2, log)))
    if cfg["wttj"]["enabled"]:
        c3 = copy.deepcopy(cfg)
        c3["wttj"]["queries"] = cfg["wttj"]["queries"][:2]
        tests.append(("Welcome to the Jungle (2 requêtes)", lambda: sources.collect_wttj(c3, log)))
    if cfg["workday"]["enabled"]:
        tests.append(("Workday", lambda: sources.collect_workday(cfg, log)))
    all_ok = True
    for name, fn in tests:
        try:
            res = fn()
            errs = []
            if isinstance(res, tuple):
                res, errs = res
            kept = [j for j in res if t._classify(j)["ok"]]
            maybe = [j for j in res if j["source"] == "LinkedIn" and not t._classify(j)["ok"]
                     and t._classify(j)["intern"] == "unknown"]
            print("%s %s : %d offres reçues, %d retenues%s"
                  % ("❌" if errs and not res else ("⚠️ " if errs else "✅"), name, len(res), len(kept),
                     (", %d à confirmer via la description" % len(maybe)) if maybe else ""))
            for e in errs:
                all_ok = False
                print("   ⚠️  %s" % e)
            for j in kept[:5]:
                print("     · %s | %s | %s" % (j.get("company"), j["title"], j.get("location")))
            if res and res[0]["source"] == "LinkedIn":
                try:
                    d = sources.linkedin_detail(res[0]["ext_id"])
                    print("   Lien carrière extrait : %s" % (d["apply_url"] or "aucun (candidature via LinkedIn)"))
                except Exception as e:
                    print("   ⚠️  détail LinkedIn : %s" % e)
        except Exception as e:
            all_ok = False
            print("❌ %s : %s" % (name, e))
        print()
    print("Résultat : %s" % ("tout fonctionne." if all_ok else
                             "au moins une source a un problème (le tracker continue avec les autres)."))


def main():
    ap = argparse.ArgumentParser(description="Tracker de stages Paris, Suisse, Singapour (IBD / S&T / AM / Commodities)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--test-notif", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--cloud", action="store_true", help="un passage, notifications ntfy, tableau dans docs/")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    cfg = load_config()

    if args.cloud:
        global SEND, DASH_PATH, dash_link
        topic = os.environ.get("NTFY_TOPIC") or cfg["cloud"]["ntfy_topic"]
        if not topic:
            sys.exit("Mode --cloud : renseigne cloud.ntfy_topic dans config.json")
        notify.NTFY_TOPIC = topic
        SEND = notify.ntfy
        os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
        # Publie la page telle quelle sur GitHub Pages, sans passer par Jekyll
        open(os.path.join(HERE, "docs", ".nojekyll"), "a").close()
        DASH_PATH = os.path.join(HERE, "docs", "index.html")
        url = cfg["cloud"]["dashboard_url"]
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if not url and "/" in repo:
            owner, name = repo.split("/", 1)
            url = "https://%s.github.io/%s/" % (owner.lower(), name)
        dash_link = (lambda: url) if url else (lambda: None)
        args.once, args.no_browser = True, True

    if args.test_notif:
        shown = SEND("Rothschild & Co · M&A / IBD", "Stage M&A (test)\n📍 Paris, France · LinkedIn",
                              "https://www.linkedin.com/jobs/")
        print("Notification système : %s (%s)" % ("affichée" if shown else "non disponible", notify.backend_name()))
        return
    if args.check:
        run_check(cfg)
        return
    if args.reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Mémoire effacée.")

    # Une seule instance : si le tracker tourne déjà, on ouvre simplement le tableau de bord
    lock = os.path.join(DATA, "tracker.pid")
    try:
        if args.cloud:
            raise OSError
        pid = int(open(lock).read().strip())
        if os.name == "nt":
            raise OSError  # os.kill(pid, 0) n'est pas un test sans effet sous Windows
        os.kill(pid, 0)
        if pid != os.getpid():
            print("Le tracker tourne déjà. Ouverture du tableau de bord.")
            webbrowser.open(dashboard.file_url(DASH_PATH))
            return
    except Exception:
        pass
    if not args.cloud:
        with open(lock, "w") as f:
            f.write(str(os.getpid()))

    store = Store(DB_PATH)
    if store.get_meta("ready_sent") is None and store.offers():
        store.set_meta("ready_sent", "1")  # tracker déjà démarré auparavant : pas de nouveau "Tracker prêt"
    tracker = Tracker(cfg, store)
    write_dashboard(store, cfg)
    log("Tracker démarré · notifications : %s · tableau de bord : %s" % (notify.backend_name(), DASH_PATH))
    if cfg["notifications"]["open_dashboard_on_start"] and not args.no_browser and not args.once:
        webbrowser.open(dashboard.file_url(DASH_PATH))

    while True:
        start = time.time()
        log("Recherche en cours…")
        try:
            new_list, seeded = tracker.cycle()
            if seeded:
                n = len(store.offers())
                log("Premier passage pour %s : offres existantes ajoutées sans notification (%d au total)."
                    % (", ".join(seeded), n))
                if store.get_meta("ready_sent") is None:  # une seule fois, pas à chaque nouvelle source
                    store.set_meta("ready_sent", "1")
                    _send(SEND, "Tracker prêt", "%d offres déjà en ligne sont dans le tableau de bord. "
                          "Tu seras notifié de chaque nouvelle offre." % n, dash_link(), button="Voir le tableau")
            tracker.notify_new(new_list)
            tracker.announce_regions()
            try:
                tracker.backfill_dates()
            except Exception:
                log("Dates de publication : erreur\n" + traceback.format_exc())
            try:
                removed = tracker.verify_offers()
                if removed:
                    log("%d offre(s) retirée(s) après lecture de la description." % removed)
            except Exception:
                log("Contrôle des descriptions : erreur\n" + traceback.format_exc())
            try:
                closed = tracker.check_closed()
                if closed:
                    log("%d offre(s) fermée(s) détectée(s)." % closed)
                tracker.maybe_digest()
            except Exception:
                log("Vérification des offres fermées / récap : erreur\n" + traceback.format_exc())
            log("Passage terminé : %d nouvelle(s) offre(s) en %ds." % (len(new_list), time.time() - start))
        except KeyboardInterrupt:
            raise
        except Exception:
            log("Erreur inattendue :\n" + traceback.format_exc())
        interval = max(3, cfg["interval_minutes"]) * 60
        sleep_for = interval + random.uniform(-60, 60)
        write_dashboard(store, cfg, next_run=time.time() + sleep_for)
        if args.once:
            break
        try:
            time.sleep(max(60, sleep_for))
        except KeyboardInterrupt:
            log("Arrêt demandé.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArrêt.")
