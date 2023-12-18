import datetime
from django.urls import reverse
from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import redirect, render
from nexus.utils.filtertree import *
from nexus.models.rcd_profiles import RCDProfile
from nexus.models.ipeds_classification import IPEDSMixin

# At some point may need to put these into a fixture to handle translations
POPULATION="Population"
POP_ALL="All Users"
POP_CONTRIB="Contributors"
CARN_CLASS="Carnegie Class."
MISSION="Mission"
PUB_PRIV="Public/Private"
PUB_PRIV_PUBLIC="Public"
PUB_PRIV_PRIVATE="Private"
EPSCOR="EPSCoR"
MSI="Minority Serving"
MSI_NOT="Not Minority Serving"
MSI_HBCU="HBCU"
MSI_HSI="HSI"
MSI_OTHER="Other MSI"
BY_YEAR="By Year"
REGION="Region"
RESEARCH_EXP="Research Exp."

INCLUDE_ALL={POPULATION, CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, BY_YEAR, REGION, RESEARCH_EXP}
INCLUDE_ALL_CONTRIBS={CARN_CLASS, MISSION, PUB_PRIV, EPSCOR, MSI, BY_YEAR, REGION, RESEARCH_EXP}

def data_viz_main(request):
    context = {
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            }
        }
    return render(request, "dataviz/vizmain.html", context)

def data_viz_demographics(request): 
    context = {
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            }
        }
    return render(request, "dataviz/demographics.html", context)

def data_viz_demographics_maps(request): 
    tree = filtertree(excludes={REGION, EPSCOR, RESEARCH_EXP})
    context = {
        "filtertree":tree,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Map Views":"dataviz:demographics_mapviews",
            }
        }
    return render(request, "dataviz/mapviews.html", context)

def data_viz_demographics_charts(request): 
    tree = filtertree(includes=INCLUDE_ALL)
    context = {
        "filtertree":tree,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Chart Views":"dataviz:demographics_cartviews",
            }
        }
    return render(request, "dataviz/chartviews.html", context)

def data_viz_demographics_scatter(request): 
    tree = filtertree(includes=INCLUDE_ALL_CONTRIBS)
    context = {
        "filtertree":tree,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Community Demographics":"dataviz:demographics",
            "Scatter Plots":"dataviz:demographics_scatterplots",
            }
        }
    return render(request, "dataviz/scatterplots.html", context)

def data_viz_capsmodeldata(request): 
    tree = filtertree(includes=INCLUDE_ALL_CONTRIBS)
    context = {
        "filtertree":tree,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Capabilities Model Data":"dataviz:capsmodeldata",
            }
        }
    return render(request, "dataviz/capsmodeldata.html", context)

def data_viz_prioritiessdata(request): 
    tree = filtertree(includes=INCLUDE_ALL_CONTRIBS)
    context = {
        "filtertree":tree,
        "breadcrumbs":{
            "Data Viewer":"dataviz:vizmain",
            "Priorities Data":"dataviz:prioritiesdata",
            }
        }
    return render(request, "dataviz/prioritiesdata.html", context)


# Must pass in a string (e.g., rcd_profiles.MissionChoices.RESEARCHESSENTIAL.label)
def getShortMissionChoice(label):
    #The Choices all have the main label marked in <b> tags. We just extract that
    return label[3:label.find("</b>")]

def filtertree(includes=None, excludes=None):
    """
    Return a filter tree for viz filtering. Use the passed param values to control what is checked and not
    Note that the collapsed state is controlled by the template (through cookies)
    """
    tree = FilterCategory()
    if (includes and POPULATION in includes) or (excludes and not POPULATION in excludes):
        tree.addChild(FilterCategory(label=POPULATION, paramName="pop", eltype=ChoiceType.RADIO,
                children=[
                    FilterChoice(label=POP_ALL, valueName="all", eltype=ChoiceType.RADIO,),
                    FilterChoice(label=POP_CONTRIB, valueName="contrib", checked=True, eltype=ChoiceType.RADIO,),
                ],
            ))
    if (includes and CARN_CLASS in includes) or (excludes and not CARN_CLASS in excludes):
        # TO-DO use the IPEDS mixin models to define the values
        tree.addChild(FilterCategory(label=CARN_CLASS, paramName="cc", 
                children=[
                    FilterChoice(label="R1", valueName="R1", checked=True,),
                    FilterChoice(label="R2", valueName="R2", checked=True,),
                    FilterChoice(label="Other Acad.", valueName="otherac", checked=True,),
                ],
            ))
    if (includes and MISSION in includes) or (excludes and not MISSION in excludes):
        tree.addChild(FilterCategory(label=MISSION, paramName="cc", 
                children=[
                    FilterChoice(label=getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHESSENTIAL.label), 
                                 valueName=RCDProfile.MissionChoices.RESEARCHESSENTIAL.value, checked=True,),
                    FilterChoice(label=getShortMissionChoice(RCDProfile.MissionChoices.RESEARCHFAVORED.label), 
                                 valueName=RCDProfile.MissionChoices.RESEARCHFAVORED.value, checked=True,),
                    FilterChoice(label=getShortMissionChoice(RCDProfile.MissionChoices.BALANCED.label), 
                                 valueName=RCDProfile.MissionChoices.BALANCED.value, checked=True,),
                    FilterChoice(label=getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGFAVORED.label), 
                                 valueName=RCDProfile.MissionChoices.TEACHINGFAVORED.value, checked=True,),
                    FilterChoice(label=getShortMissionChoice(RCDProfile.MissionChoices.TEACHINGESSENTIAL.label), 
                                 valueName=RCDProfile.MissionChoices.TEACHINGESSENTIAL.value, checked=True,),
                ],
            ))
    if (includes and PUB_PRIV in includes) or (excludes and not PUB_PRIV in excludes):
        # TO-DO use the IPEDS mixin models to define the values
        tree.addChild(FilterCategory(label=PUB_PRIV, paramName="pub_priv",
                children=[
                    FilterChoice(label=PUB_PRIV_PUBLIC, valueName="pub", checked=True, ),
                    FilterChoice(label=PUB_PRIV_PRIVATE, valueName="priv", checked=True, ),
                ],
            ))
    if (includes and EPSCOR in includes) or (excludes and not EPSCOR in excludes):
        # TO-DO use the IPEDS mixin models to define the values
        tree.addChild(FilterCategory(label=EPSCOR, paramName="epscor",
                children=[
                    FilterChoice(label="EPSCoR", valueName="yes", checked=True, ),
                    FilterChoice(label="Non-EPSCoR", valueName="no", checked=True, ),
                ],
            ))
    if (includes and MSI in includes) or (excludes and not MSI in excludes):
        tree.addChild(FilterCategory(label=MSI, paramName="msi",
                children=[
                    FilterChoice(label=MSI_NOT, valueName="not", checked=True, ),
                    FilterChoice(label=MSI_HBCU, valueName="hbcu", checked=True, ),
                    FilterChoice(label=MSI_HSI, valueName="hsi", checked=True, ),
                    FilterChoice(label=MSI_OTHER, valueName="other", checked=True, ),
                ],
            ))
    if (includes and BY_YEAR in includes) or (excludes and not BY_YEAR in excludes):
        children = []
        thisyear = datetime.date.today().year
        for year in range(2020, thisyear):
            yrStr = str(year)
            children.append(FilterChoice(label=yrStr, valueName=yrStr, checked=True))
        tree.addChild(FilterCategory(label=BY_YEAR, paramName="year", collapsed=True, children=children))
    
    if (includes and REGION in includes) or (excludes and not REGION in excludes):
        # TO-DO Need to filter those that have too few members in the data to be interesting
        tree.addChild(FilterCategory(label=REGION, paramName="region", collapsed=True,
                children=[
                    FilterChoice(label=IPEDSMixin.RegionChoices.SERVICE_SCHOOLS.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.SERVICE_SCHOOLS.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.NEW_ENGLAND.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.NEW_ENGLAND.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.MID_EAST.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.MID_EAST.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.GREAT_LAKES.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.GREAT_LAKES.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.PLAINS.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.PLAINS.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.SOUTHEAST.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.SOUTHEAST.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.SOUTHWEST.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.SOUTHWEST.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.ROCKY_MOUNTAINS.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.ROCKY_MOUNTAINS.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.FAR_WEST.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.FAR_WEST.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.OTHER_U_S_JURISDICTIONS.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.OTHER_U_S_JURISDICTIONS.value), checked=True,),
                    FilterChoice(label=IPEDSMixin.RegionChoices.CANADA.label, 
                                 valueName=str(IPEDSMixin.RegionChoices.CANADA.value), checked=True,),
                ],
            ))

    return tree

#RESEARCH_EXP="Research Exp."
