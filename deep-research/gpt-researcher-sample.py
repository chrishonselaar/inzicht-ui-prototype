from gpt_researcher import GPTResearcher
import asyncio

async def get_report(query: str, report_type: str) -> str:
    researcher = GPTResearcher(query, report_type)
    await researcher.conduct_research()
    report = await researcher.write_report()
    return report

if __name__ == "__main__":
    query = "Welke bewezen effectieve klimaatadaptatiemaatregelen implementeren Nederlandse gemeenten in hun historische binnensteden, met specifieke aandacht voor de balans tussen klimaatbestendigheid en behoud van cultuurhistorische waarden, en wat zijn de geleerde lessen uit pilotprojecten en evaluaties?"
    report_type = "research_report"
    report = asyncio.run(get_report(query, report_type))
    print(report)
