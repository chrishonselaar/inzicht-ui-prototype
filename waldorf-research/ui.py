import streamlit as st

# Add example questions dictionary
EXAMPLE_QUESTIONS = {
    "Historische Besluitvorming": [
        "Wat hebben we vorig jaar besloten over de transgenderwet-motie?",
        "Toon alle discussies over geluidsklachten bij evenementen in het Stadspark van de afgelopen 2 jaar",
        "Wanneer zijn we begonnen met het bespreken van het detailhandelsbeleid voor de binnenstad?"
    ],
    "Precedentonderzoek": [
        "Hebben we eerder vergelijkbare moties aangenomen over lobbyen bij de rijksoverheid?",
        "Welke andere keren hebben we bestemmingsplanwijzigingen besproken?",
        "Hoe zijn we in het verleden omgegaan met vergelijkbare verzoeken voor kinderopvangfinanciering?"
    ],
    "Beleidsontwikkeling": [
        "Welke toezeggingen hebben we gedaan over duurzaamheid in verschillende beleidsdocumenten?",
        "Toon alle discussies over huisvestingsbeleid voor ouderen in verschillende documenten",
        "Wat hebben verschillende partijen gezegd over de diversiteit van winkels in de binnenstad?"
    ],
    "Procedurele Vragen": [
        "Wat was het stempatroon bij vergelijkbare moties?",
        "Hoe zijn we in het verleden omgegaan met amendementen op conformstukken?",
        "Wat is onze standaardprocedure voor het behandelen van moties vreemd?"
    ],
    "Budgetbewaking": [
        "Waar hebben we eerder geld uit de algemene middelen voor gealloceerd?",
        "Welke andere projecten hebben we gefinancierd uit het energietransitiefonds?",
        "Hoe zijn we omgegaan met vergelijkbare financieringsverzoeken voor sociale projecten?"
    ],
    "Kruisverwijzingen": [
        "Zijn er tegenstrijdigheden tussen onze verschillende beleidslijnen over evenementengeluid?",
        "Hoe verhoudt dit woningbouwvoorstel zich tot onze eerdere besluiten over Meerstad?",
        "Welke andere documenten verwijzen naar de Sociale Basis?"
    ],
    "Contextopbouw": [
        "Wat was de discussie die leidde tot dit besluit?",
        "Toon alle relevante achtergrondinformatie over de Wingerd kinderopvangsituatie",
        "Wat waren de belangrijkste argumenten in eerdere debatten over dit onderwerp?"
    ],
    "Stakeholder Input": [
        "Wat hebben verschillende belanghebbenden gezegd over het winkelbeleid in eerdere vergaderingen?",
        "Wanneer heeft de Groningen City Club voor het laatst input geleverd over binnenstad beleid?",
        "Welke feedback hebben we ontvangen van bewoners over evenementengeluid?"
    ],
    "Implementatie Opvolging": [
        "Welke toezeggingen hebben we gedaan over de opvolging van dit beleid?",
        "Zijn er specifieke deadlines of mijlpalen vastgesteld voor dit project?",
        "Welke monitoringseisen hebben we vastgesteld?"
    ],
    "Politieke Analyse": [
        "Hoe hebben verschillende partijen gestemd over vergelijkbare kwesties?",
        "Welke standpunten hebben partijen ingenomen over de diversiteit van winkels door de tijd heen?",
        "Hoe is de coalitie omgegaan met vergelijkbare financieringsverzoeken?"
    ],
    "Actuele Beleidsvergelijking": [
        "Hoe pakt onze aanpak van het woonbeleid uit vergeleken met andere studentensteden in Nederland?",
        "Wat zijn de laatste wetenschappelijke inzichten over binnenstedelijke verdichting en hoe verhoudt ons beleid zich daartoe?",
        "Welke innovatieve oplossingen voor geluidsoverlast bij evenementen worden in andere steden toegepast?"
    ],
    "Maatschappelijke Context": [
        "Hoe wordt er in sociale media gereageerd op ons nieuwe horecabeleid voor de binnenstad?",
        "Wat schrijven lokale en nationale media over onze aanpak van de energietransitie?",
        "Welke ervaringen hebben andere gemeenten met soortgelijke regelgeving voor kleine retailers?"
    ],
    "Wetenschappelijke Onderbouwing": [
        "Wat zegt recent onderzoek over de effectiviteit van zonneweides versus zonnepanelen op daken?",
        "Welke academische studies zijn er over de impact van studentenhuisvesting op wijken?",
        "Wat zijn de laatste inzichten uit onderzoek naar sociale cohesie in wijken met veel internationale bewoners?"
    ],
    "Trend Analyse": [
        "Hoe verhoudt de ontwikkeling van onze winkelstraten zich tot landelijke trends in retail?",
        "Wat zijn de voorspellingen voor bevolkingsgroei in studentensteden en hoe bereiden andere steden zich voor?",
        "Welke innovatieve participatiemodellen worden in andere gemeenten toegepast?"
    ],
    "Beleidsimpact": [
        "Wat zijn de effecten van vergelijkbaar detailhandelsbeleid in andere historische binnensteden?",
        "Hoe wordt er in vakpublicaties geoordeeld over ons armoedebeleid?",
        "Welke best practices zijn er voor het betrekken van jongeren bij gemeentelijk beleid?"
    ],
    "Toekomstverkenning": [
        "Welke technologische ontwikkelingen komen er aan die relevant zijn voor ons parkeerbeleid?",
        "Wat zijn de verwachtingen voor de toekomst van binnenstedelijke culturele voorzieningen?",
        "Hoe bereiden andere gemeenten zich voor op klimaatadaptatie in historische binnensteden?"
    ],
    "Historische Beleidsontwikkeling": [
        "Hoe heeft ons fietsbeleid zich ontwikkeld sinds de jaren '70 en hoe verhoudt zich dat tot andere Nederlandse steden?",
        "Wat waren de argumenten bij de invoering van autoluwe zones in de binnenstad en hoe kijken experts daar nu op terug?",
        "Welke lessen kunnen we leren uit 50 jaar studentenhuisvestingsbeleid in Groningen?"
    ],
    "Lange Termijn Impact": [
        "Hoe heeft de ontwikkeling van het Zernike Campus de stad beïnvloed en wat kunnen we daarvan leren voor Suikerzijde?",
        "Wat waren de verwachtingen bij de start van Meerstad en hoe verhouden die zich tot de huidige realiteit?",
        "Welke effecten heeft de invoering van het betaald parkeren gehad in verschillende wijken?"
    ],
    "Vergelijkende Analyses": [
        "Hoe verhouden onze ervaringen met wijkvernieuwing zich tot soortgelijke projecten in andere steden?",
        "Wat kunnen we leren van eerdere pogingen om de retail in de binnenstad te reguleren?",
        "Welke parallellen zijn er tussen de huidige woningcrisis en vergelijkbare situaties in het verleden?"
    ],
    "Beleidsevaluatie met Context": [
        "Wat waren de doelstellingen van ons duurzaamheidsbeleid in de jaren '90 en hoe kijken experts nu naar die aanpak?",
        "Hoe effectief zijn onze maatregelen tegen studentenoverlast geweest volgens zowel gemeentelijke bronnen als onderzoek?",
        "Welke innovaties in burgerparticipatie hebben we geprobeerd en wat zeggen studies over de effectiviteit?"
    ],
    "Trendanalyse met Historisch Perspectief": [
        "Hoe heeft de samenstelling van de binnenstad zich ontwikkeld en wat zegt dat over de huidige retail-discussie?",
        "Wat kunnen we leren van eerdere economische crises en hun impact op de lokale economie?",
        "Hoe heeft de gemeentelijke dienstverlening zich ontwikkeld en wat zijn de laatste inzichten hierover?"
    ],
    "Maatschappelijke Ontwikkelingen": [
        "Hoe is de gemeente omgegaan met verschillende vluchtelingenstromen en wat kunnen we daarvan leren?",
        "Wat was de impact van eerdere energietransities (zoals van kolen naar gas) op de stad?",
        "Hoe heeft de gemeente ingespeeld op veranderende demografische patronen?"
    ]
}

def init_sidebar():
    """Initialize the sidebar with logo and information."""
    with st.sidebar:        
        st.image("waldorf-research/assets/logo.png", width=150)
        
        # Display example questions using the dictionary
        with st.expander("Voorbeelden van vragen", expanded=False):
            for category, questions in EXAMPLE_QUESTIONS.items():
                st.markdown(f"### {category}")
                for question in questions:
                    st.markdown(f"- {question}")

        st.markdown("""
### Hoe gebruikt u inzichtNL?

- Voorbereiding op debatten en besluitvorming
- Snel overzicht op complexe dossiers
- Waarborgen van consistentie in beleidsvorming
- Volgen van de implementatie van besluiten
- Begrip van de historische context van actuele kwesties      

### Welke bronnen combineert inzichtNL?

- Gemeentelijke documenten
- Overheidspublicaties
- Wetenschappelijke studies
- Persberichten
- Social media                            
""")
