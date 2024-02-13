from django.shortcuts import render
from nexus.models import CapabilitiesAnswer, Institution, RCDProfile
from django.http import JsonResponse
import pandas as pd
import plotly.express as px
import plotly.io as po
from django.db.models import Q


def filter_assessment_data(request):
    """Translate URL query parameters into a filter for CapabilitiesAnswer objects."""
    answers = CapabilitiesAnswer.objects.all()

    # TODO filter by contributor status (all / contrib only)
    # TODO filter by EPSCOR
    # TODO filter by MSI

    if carnegie_classifications := request.GET.get('carnegie_classification'):
        cc = carnegie_classifications.split(',')
        values = set()
        filters = Q(assessment__profile__institution__carnegie_classification__in=values)

        if "R1" in cc:
            values.add(Institution.CarnegieClassificationChoices.R1)
        if "R2" in cc:
            values.add(Institution.CarnegieClassificationChoices.R2)

        if "otherac" in cc:
            # Note: this assumes that R1 and R2 are the numerically first two values in the CarnegieClassificationChoices
            filters |= Q(assessment__profile__institution__carnegie_classification__gt=Institution.CarnegieClassificationChoices.R2)

            # But some could also be null
            filters |= Q(assessment__profile__institution__carnegie_classification=None)

        answers = answers.filter(filters)

    if missions := request.GET.get('mission'):
        answers = answers.filter(assessment__profile__mission__in=missions.split(','))

    if pub_privs := request.GET.get('pub_priv'):
        pp = pub_privs.split(',')
        values = set()

        if "pub" in pp:
            values.add(Institution.ControlChoices.PUBLIC)

        if "priv" in pp:
            values.add(Institution.ControlChoices.PRIVATE_FOR_PROFIT)
            values.add(Institution.ControlChoices.PRIVATE_NON_PROFIT)

        answers = answers.filter(assessment__profile__institution__ipeds_control__in=values)

    if years := request.GET.get('year'):
        answers = answers.filter(assessment__profile__year__in=years.split(','))

    if regions := request.GET.get('region'):
        r = regions.split(',')
        values = set()

        if "serviceschools" in r:
            values.add(Institution.RegionChoices.SERVICE_SCHOOLS)
        if "new_england" in r:
            values.add(Institution.RegionChoices.NEW_ENGLAND)
        if "mid_east" in r:
            values.add(Institution.RegionChoices.MID_EAST)
        if "great_lakes" in r:
            values.add(Institution.RegionChoices.GREAT_LAKES)
        if "plains" in r:
            values.add(Institution.RegionChoices.PLAINS)
        if "southeast" in r:
            values.add(Institution.RegionChoices.SOUTHEAST)
        if "southwest" in r:
            values.add(Institution.RegionChoices.SOUTHWEST)
        if "rocky_mountains" in r:
            values.add(Institution.RegionChoices.ROCKY_MOUNTAINS)
        if "far_west" in r:
            values.add(Institution.RegionChoices.FAR_WEST)
        if "other_us" in r:
            values.add(Institution.RegionChoices.OTHER_U_S_JURISDICTIONS)
        if "canada" in r:
            values.add(Institution.RegionChoices.CANADA)

        answers = answers.filter(assessment__profile__institution__ipeds_region__in=values)

    if facets := request.GET.get('facet'):
        f = facets.split(',')
        facets = list()

        if "carnegie_classification" in f:
            facets.append("assessment__profile__institution__carnegie_classification")
        if "facing" in f:
            facets.append("question__topic__facing")

        answers = answers.aggregate_score(*facets)
    return answers.aggregate_score()


# % %
colorPalette = {'allData':'#9F9F9F', 'EPSCoR':'#5ab4ac', 'nonEPSCoR':'#d8b365', 
                'errBars':'#bbb', 'lightErrBars':'#f5f5f5', 'bgColor':'#555',
                'RF':'#40bad2', 'DF': '#fab900', 'SWF':'#90bb23', 'SYF':'#ee7008', 'SPF':'#d5393d',
                'R1':'#2e75b6','R2':'#8bb8e1','AllButR1':'#d1e3f3','OtherAcad':'#d1e3f3',
                'Public':'#ffd966','Private':'#ec7728',
                'NotMSI':'#FFE699','HSI':'#C5E0B4','otherMSI':'#8FAADC',
                '2022':'#ffba5a', '2021':'#6aaa96', '2020':'#ada3d3'}
    
# Define a dictionary to map classification values to names
classification_mapping = {
        15.0: 'R1', 16.0: 'R2', 17.0: 'R3', 18.0: 'M1', 19.0:'M2', 20.0:'M3', 21.0:"Bacc: Arts and Sci", 22.0:"Bacc: Diverse", 
        27.0: "4yr: Research Institutions", 0: 'Other'}
# Define a dictionary to map classification values to names

Facing_mapping = { 1: 'Researcher-Facing', 2: 'Data-Facing', 3: 'Software-Facing', 4 : 'System-Facing', 5: 'Strategy & Planning Facing'}

def allSummaryDataGraph():
        
        data = CapabilitiesAnswer.objects.aggregate_score('question__topic__facing').values('question__topic__facing','average','stddev')
        
        # Convert the queryset to a DataFrame
        df = pd.DataFrame(data)
        
        # Map the classification values to names
        df['question__topic__facing'] = df['question__topic__facing'].map(Facing_mapping)

        data = df
        #print(data)

        # Rename the columns for clarity
        data = data.rename(columns={

                'average':'Average Values',
                'question__topic__facing' : 'Facings',
                'stddev' : 'Std Dev'
            })

        print(data)

        # Convert into the percentage
        data['Average Values'] *= 100
        data['Std Dev'] *= 100
        
        # Create a All Summary Data bar chart
        
        fig = px.bar(data, x='Facings', y= 'Average Values', error_y='Std Dev',width=800, height=600,color_discrete_map={'': colorPalette['allData']})

        fig.update_layout(
        title=dict(text='All Data Summary Graph By Facings', font=dict(size=20, family='Arial')),
        xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
        yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
        plot_bgcolor=colorPalette['bgColor']    )

        # Change the color of error bars
        fig.update_traces(error_y_color='#bbb',marker_line_color='black', marker_line_width=1.5)

        # Update the layout to set y-axis tickformat to percentages
        fig.update_layout(yaxis=dict(tickformat='%d% %'))  # Set tickformat to display percentages
        
        # Set the bar edge color
        #fig.update_traces(marker_line_color='black', marker_line_width=1.5)
        

        # fig.update_layout()

        # Set grid color and linestyle for y-axis
        fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)

        # Convert the figure to HTML including Plotly.js
        return po.to_html(fig, include_plotlyjs='cdn', full_html=True)
       # return  {'visualization': img}

def simpleCC():
    data =  CapabilitiesAnswer.objects.aggregate_score('question__topic__facing','assessment__profile__institution__carnegie_classification').values('question__topic__facing','assessment__profile__institution__carnegie_classification','average','stddev')
    
    # Convert the queryset to a DataFrame
    CCdata = pd.DataFrame(data)
    #print(CCdata)

    # Values to drop
    # values_to_drop = [17.0, 18.0, 19.0, 21.0, 22.0, 27.0, float('nan')]

    # Drop rows with specified values
#   CCdata = CCdata[~CCdata['assessment__profile__institution__carnegie_classification'].isin(values_to_drop)]

    # Print the resulting DataFrame
#    print(CCdata)


    # Map the classification values to names
    CCdata['question__topic__facing'] = CCdata['question__topic__facing'].map(Facing_mapping)
    

    # Map the classification values to names
    
    CCdata['assessment__profile__institution__carnegie_classification'] = CCdata['assessment__profile__institution__carnegie_classification'].fillna(0)
    CCdata['assessment__profile__institution__carnegie_classification'] = CCdata['assessment__profile__institution__carnegie_classification'].\
        map(classification_mapping)
    
    for i in CCdata.index:
        if ((CCdata['assessment__profile__institution__carnegie_classification'][i] == 'R1') or (CCdata['assessment__profile__institution__carnegie_classification'][i]== 'R2') or (CCdata['assessment__profile__institution__carnegie_classification'][i] == 'Other')):
            pass
        else:
            CCdata['assessment__profile__institution__carnegie_classification'][i] = 'OtherAcad'


    data1 = CCdata.loc[CCdata['assessment__profile__institution__carnegie_classification']=='OtherAcad'].groupby(['question__topic__facing']).mean(numeric_only=True)
    
    data1 = CCdata.loc[CCdata['assessment__profile__institution__carnegie_classification']=='OtherAcad'].groupby(['question__topic__facing']).std(numeric_only=True)
    
    data1['assessment__profile__institution__carnegie_classification'] = ['OtherAcad','OtherAcad','OtherAcad','OtherAcad','OtherAcad']
    
    # Reset index to convert 'question__topic__facing' to a regular column
    data1.reset_index(inplace=True)
    
    data1.rename(columns={'index': 'question__topic__facing'}, inplace=True) 
    
    #print(data1)
    

    # Filter only 'R1' and 'R2' values
    CCdatafilter = CCdata[CCdata['assessment__profile__institution__carnegie_classification'].isin(['R1', 'R2'])]
      
    
    # Combine both datasets
    simpleCC = pd.concat([CCdatafilter, data1],ignore_index=True)

    # Reset index
    #combined_df.reset_index(drop=True, inplace=True)

    print(simpleCC)
    
    # Rename the columns for clarity
    simpleCC= simpleCC.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__carnegie_classification' : 'Carnegie Classification',
            'average':'Average Values',
            'stddev' : 'Std Dev'
        })
    
    #Multiply by 100
    simpleCC['Average Values'] *= 100
    simpleCC['Std Dev'] *= 100
    
    
    # Create a grouped bar chart
    fig = px.bar(simpleCC, x='Facings', y='Average Values',error_y= 'Std Dev',
                    color='Carnegie Classification', color_discrete_map={'R1':colorPalette['R1'], 'R2':colorPalette['R2'],'OtherAcad':colorPalette['OtherAcad']},
                    barmode='group', # Use 'group' for grouped bars
                    labels={'question__topic__facing': '', 'average': ''},
                    title='Simple Carnegie Classification Facing Graphs',
                    width=800, height=600 
                 )
  
    # Change the color of error bars
    fig.update_traces(error_y_color='#bbb')  
    
    # Change font size and font type
    fig.update_layout(
    xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
    yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
    plot_bgcolor=colorPalette['bgColor']
    )
    
    # Update the layout to set y-axis tickformat to percentages
    fig.update_layout(yaxis=dict(tickformat='%d% %'))  # Set tickformat to display percentages
    
    # Set the bar edge color
    fig.update_traces(marker_line_color='black', marker_line_width=1.5)
    

    #fig1.update_layout(plot_bgcolor=colorPalette['bgColor'])

    # Set grid color and linestyle for y-axis
    #ebColor = 'black'  # Replace with your desired grid color
    fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)

    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)
    #return  {'viz1': img}


def publicPrivateGraph():
        # Create the figure that shows per-facing coverage for Public and Privates

    data = CapabilitiesAnswer.objects.aggregate_score('question__topic__facing','assessment__profile__institution__ipeds_control'). \
    values('question__topic__facing','assessment__profile__institution__ipeds_control','average','stddev')

    
    data1= pd.DataFrame(data)
    #print("\nPPData:",data1)

    # Values to drop
    values_to_drop = [float('NaN')]

    # Drop rows with specified values
    facingsdataset = data1[~data1['assessment__profile__institution__ipeds_control'].isin(values_to_drop)]
    
    # Print the resulting DataFrame
    print("\nPrivate-Public Data \n", facingsdataset)
    
    # Map the classification values to names
    facingsdataset['question__topic__facing'] = facingsdataset['question__topic__facing'].map(Facing_mapping)
    
    # Define a dictionary to map classification values to names
    classification_mapping = {
        1: 'Public',
        2: 'Private'
        }
    
    # Map the classification values to names
    facingsdataset['assessment__profile__institution__ipeds_control'] =  facingsdataset['assessment__profile__institution__ipeds_control'].\
        map(classification_mapping)
    
    
    # Rename the columns for clarity
    facingsdataset =  facingsdataset.rename(columns={
            'question__topic__facing' : 'Facings',
            'assessment__profile__institution__ipeds_control' :'Public/Private',
            'average':'Average Values',
            'stddev' : 'Std Dev'
        })
    #Multiply by 100
    facingsdataset['Average Values'] *= 100
    facingsdataset['Std Dev'] *= 100

    print("Public/Private Date:\n", facingsdataset)
    
    
    # Create a grouped bar chart
    fig = px.bar( facingsdataset, x='Facings', y='Average Values',error_y='Std Dev',
                    barmode='group',  # Use 'group' for grouped bars
                    color='Public/Private',
                    color_discrete_map={'Public': colorPalette['Public'], 'Private': colorPalette['Private']},  # Set custom color
                    labels={'Facings': 'Facings', 'value': 'Average Values'},
                    title='Public/Private Facing Graphs',
                    width=800, height=600)

    # Set empty legend title 
    fig.update_layout(legend_title_text='')
    
    # Change font size and font type
    fig.update_layout(
    xaxis=dict(title=dict(text='', font=dict(size=16, family='Arial'))),
    yaxis=dict(title=dict(text='', font=dict(size=16, family='Arial')))
    )
    
    # Change the color of error bars
    fig.update_traces(error_y_color='#bbb')

    # Set the bar edge color
    fig.update_traces(marker_line_color='black', marker_line_width=1.5)
    

    fig.update_layout(plot_bgcolor=colorPalette['bgColor'])

    # Set grid color and linestyle for y-axis
    ebColor = 'black'  # Replace with your desired grid color
    fig.update_yaxes(gridcolor=colorPalette['errBars'], gridwidth=0.5, griddash='dot',zeroline=False)


    # Convert the figure to HTML including Plotly.js
    return po.to_html(fig, include_plotlyjs='cdn', full_html=True)
   
def index(request):
    
    # fetchinng filter assessment data from a request
    data = filter_assessment_data(request)
   # print(data)

    # Convert the queryset to a DataFrame
    filter_data = pd.DataFrame(data)
  # print(filter_data)  

    context = {'visualization':allSummaryDataGraph(),'viz1': simpleCC(),'viz2':publicPrivateGraph()}
  #  context = {'viz1': simpleCC()}
    return render(request, 'viz/test.html',context)
    