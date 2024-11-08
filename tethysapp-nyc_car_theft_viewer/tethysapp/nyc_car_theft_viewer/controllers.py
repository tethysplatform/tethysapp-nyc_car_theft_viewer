from django.http import JsonResponse

from pathlib import Path
import json
from datetime import datetime, timedelta

from sodapy import Socrata

from tethys_sdk.layouts import MapLayout
from tethys_sdk.routing import controller
from tethys_sdk.gizmos import SelectInput, TextInput, Button, DatePicker

from .app import NycCarTheftViewer as App

@controller(name='home', app_workspace=True)
class NYCCarTheftViewerMap(MapLayout):
    app = App
    base_template = 'nyc_car_theft_viewer/base.html'
    template_name = 'nyc_car_theft_viewer/home.html'
    map_title = 'NYC Car Theft Viewer'
    show_properties_popup=True
    plot_slide_sheet = True
    show_legends = True

    basemaps = ['OpenStreetMap', 'ESRI']
    default_map_extent=[-74.40251381902671, 40.4396142607784, -73.48612422304846, 40.969123112654955]

    def compose_layers(self, request, map_view, app_workspace, *args, **kwargs):
        # Load GeoJSON file
        geojson_file = Path(app_workspace.path) / 'nyc_car_theft_tracker' / 'data' / 'borough_boundaries.geojson'

        # Load GeoJSON data
        with open(geojson_file) as f:
            geojson_data = json.load(f)

        # Build GeoJSON layer for borough boundaries
        borough_boundaries_layer = self.build_geojson_layer(
            geojson=geojson_data,
            layer_name='Borough Boundaries',
            layer_title='Borough Boundaries',
            layer_variable='borough_boundaries_layer_var',
            visible=True,
            selectable=True,
            plottable = True
        )

        layer_groups = [
            self.build_layer_group(
                id='borough_boundaries_group',
                display_name='Borough Boundaries',
                layer_control='checkbox',
                layers=[borough_boundaries_layer],
            )
        ]

        return layer_groups
    
    def get_context(self, request, *args, **kwargs):
        # Create form gizmos
        borough = SelectInput(display_text='Borough', name='borough', 
                              multiple=False, options=[('Select a borough', ''),
                                                       ('Bronx', 'bronx'), 
                                                       ('Brooklyn', 'brooklyn'), 
                                                       ('Manhattan', 'manhattan'), 
                                                       ('Queens', 'queens'), 
                                                       ('Staten Island', 'staten_island')])
                
        start_date_picker = DatePicker(display_text='Start Date', name='start_date', initial='09/30/2024', end_date='09/30/2024', attributes={"class": "form-input"})
        end_date_picker = DatePicker(display_text='End Date', name='end_date', initial='09/30/2024', end_date='09/30/2024', attributes={"class": "form-input"})
        grouping_picker = SelectInput(display_text='Group by', name='group_by', multiple=False, options=[('Time of day', 'time_of_day'), ('Day of week', 'day_of_week'), ('Month', 'month')], initial='time_of_day')
        submit_button = Button(display_text='Search', name='submit', submit=True, style='success', attributes={"form": "search-form"})

        # Get current plot settings
        plot_start_date_setting_val = self.app.get_custom_setting('plot_start_date')
        plot_end_date_setting_val = self.app.get_custom_setting('plot_end_date')
        sort_type_setting_val = self.app.get_custom_setting('sort_type')

        plot_start_date_picker = DatePicker(display_text='Plot Start Date', name='plot_start_date', initial=plot_start_date_setting_val, end_date='09/30/2024', attributes={"class": "form-input"})
        plot_end_date_picker = DatePicker(display_text='Plot End Date', name='plot_end_date', initial=plot_end_date_setting_val, end_date='09/30/2024', attributes={"class": "form-input"})
        sort_type = SelectInput(display_text='Sort Type', name='sort_type', multiple=False, options=[('Month', 'month'), ('Week', 'week')], initial=sort_type_setting_val)
        update_settings_button = Button(display_text='Update Plot Settings', name='update_settings', submit=True, style='success', attributes={"form": "update-settings-form"})

        # Prepare context and add gizmos
        context = super().get_context(request, *args, **kwargs)
        context['borough'] = borough
        context['start_date'] = start_date_picker
        context['end_date'] = end_date_picker
        context['group_by'] = grouping_picker
        context['submit_button'] = submit_button

        context['plot_start_date'] = plot_start_date_picker
        context['plot_end_date'] = plot_end_date_picker
        context['sort_type'] = sort_type
        context['update_settings_button'] = update_settings_button

        return context
    
    def group_graph_results(self, results, time_period):
        """Group the results of a query by the specified time period."""
        grouped_results = {}
        if time_period == 'week':
            for result in results['results']:
                date = result['date']
                date_obj = datetime.strptime(date, '%m/%d/%Y')
                start_of_week = date_obj - timedelta(days=date_obj.weekday())
                end_of_week = start_of_week + timedelta(days=6)

                week_range = f"{start_of_week.strftime('%m/%d/%y')} - {end_of_week.strftime('%m/%d/%y')}"
                # Add week range to grouped results
                if week_range not in grouped_results:
                    grouped_results[week_range] = 0
                # Increment count for week range
                grouped_results[week_range] += 1

            # Sort the grouped results by week range
            time_series = sorted(
                grouped_results.keys(),
                key=lambda x: datetime.strptime(x.split(' - ')[0], '%m/%d/%y')
            )

        if time_period == 'month':
            for result in results['results']:
                date = result['date']
                month = datetime.strptime(date, '%m/%d/%Y').strftime('%Y-%m')
                # Add month to grouped results
                if month not in grouped_results:
                    grouped_results[month] = 0
                # Increment count for month
                grouped_results[month] += 1

            # Sort the grouped results by month
            time_series = sorted(grouped_results.keys())
        
        # Get the y values for the plot
        grouped_results = [grouped_results[period] for period in time_series]

        return time_series, grouped_results
    
    def get_plot_for_layer_feature(self, request, layer_name, feature_id, layer_data, 
                                feature_props, app_workspace, *args, **kwargs):    
        """Override the default get_plot_for_layer_feature method to return a bar plot of car thefts """
        # Format the borough name for displaying in the plot title
        borough = feature_props['boro_name'].upper()

        # Get the start and end dates, and sort type from the app settings
        start_date = self.app.get_custom_setting('plot_start_date')
        end_date = self.app.get_custom_setting('plot_end_date')
        sort_type = self.app.get_custom_setting('sort_type')
        
        # Run the query and group the results for graphing
        results = self.run_query(borough, start_date, end_date)
        x_values, y_values =  self.group_graph_results(results, sort_type)
        
        return (f"Car Theft in {borough.capitalize()} from {start_date} to {end_date}", 
                [{'x': x_values, 'y': y_values, 'type': 'bar'}], 
                {"yaxis": {'title': 'Number of Car Thefts'}})

    def search_form(self, request, *args, **kwargs):
        """REST endpoint for the search form."""
        form_data = request.POST
        
        borough = form_data.get('borough')
        start_date = form_data.get('start_date')
        end_date = form_data.get('end_date')
        group_by = form_data.get('group_by')
        
        # Handle invalid form data
        if not borough:
            return JsonResponse({'error': 'Please select a borough.'}, status=400)

        if start_date > end_date:
            return JsonResponse({'error': 'Start date must be before end date.'}, status=400)

        # Run the query and color code the results based on the selected grouping option
        query_results = self.run_query(borough, start_date, end_date)
        color_coded_results = self.color_code_results(query_results, group_by)

        return JsonResponse(color_coded_results)
    
    def color_code_results(self, results, group_by):
        """Color code the results based on the selected grouping option."""
        # Define color options for each grouping option and intialize counts to display in the legend
        reference_options = {
            "time_of_day": {'Morning': ['blue', 0], 'Afternoon': ['green', 0], 'Evening': ['red', 0]},
            "day_of_week": {'Monday': ['blue', 0], 'Tuesday': ['green', 0], 'Wednesday': ['yellow', 0], 
                    'Thursday': ['orange', 0], 'Friday': ['red', 0], 'Saturday': ['purple', 0], 
                    'Sunday': ['pink', 0]},
            "month": {'January': ['lightblue', 0], 'February': ['lightgreen', 0], 'March': ['yellow', 0],
                  'April': ['darkblue', 0], 'May': ['red', 0], 'June': ['purple', 0],
                  'July': ['pink', 0], 'August': ['brown', 0], 'September': ['darkgreen', 0],
                  'October': ['orange', 0], 'November': ['gray', 0], 'December': ['cyan', 0]}
        }

        reference = reference_options[group_by]
        if group_by == "time_of_day":
            for result in results['results']:
                time = datetime.strptime(result['time'], '%H:%M:%S')
                if time < datetime.strptime('12:00:00', '%H:%M:%S'):
                    # Color code the individual result based on the time of day
                    result['color'] = reference['Morning'][0]
                    # Increment the count for the time of day
                    reference['Morning'][1] += 1
                elif time < datetime.strptime('17:00:00', '%H:%M:%S'):
                    # Color code the individual result based on the time of day
                    result['color'] = reference['Afternoon'][0]
                    # Increment the count for the time of day
                    reference['Afternoon'][1] += 1
                else:
                    # Color code the individual result based on the time of day
                    result['color'] = reference['Evening'][0]
                    # Increment the count for the time of day
                    reference['Evening'][1] += 1

        elif group_by == "day_of_week":
            for result in results['results']:
                date = datetime.strptime(result['date'], '%m/%d/%Y')
                day_of_week = date.strftime('%A')

                # Color code the individual result based on the day of the week
                result['color'] = reference[day_of_week][0]
                # Increment the count for the day of the week
                reference[day_of_week][1] += 1

        elif group_by == "month":
            for result in results['results']:
                date = datetime.strptime(result['date'], '%m/%d/%Y')
                month = date.strftime('%B')

                # Color code the individual result based on the month
                result['color'] = reference[month][0]
                # Increment the count for the month
                reference[month][1] += 1

        # Add the legend data to the results
        results['legend'] = reference

        return results

    def update_settings_form(self, request, *args, **kwargs):
        """REST endpoint for the update settings form."""
        form_data = request.POST

        plot_start_date = form_data.get('plot_start_date')
        plot_end_date = form_data.get('plot_end_date')
        sort_type = form_data.get('sort_type')

        if plot_start_date > plot_end_date:
            return JsonResponse({'error': 'Plot start date must be before plot end date.'}, status=400)

        # Update the app settings
        self.app.set_custom_setting('plot_start_date', plot_start_date)
        self.app.set_custom_setting('plot_end_date', plot_end_date)
        self.app.set_custom_setting('sort_type', sort_type)

        return JsonResponse({'success': 'Settings updated successfully!'})

    def run_query(self, borough, start_date, end_date):
        """Run a query to get car theft data for the specified borough and date range."""
        client = Socrata("data.cityofnewyork.us", None)

        start_date_object = datetime.strptime(start_date, "%m/%d/%Y")
        end_date_object = datetime.strptime(end_date, "%m/%d/%Y")
        # Format the dates for the query
        start_date = start_date_object.strftime('%Y-%m-%d')
        end_date = end_date_object.strftime('%Y-%m-%d')

        # Container to hold all results that the API returns
        all_results = []
        # Form the where clause for the query to filter by borough and date range
        where_clause = f"boro_nm='{borough.upper()}' AND cmplnt_fr_dt BETWEEN '{start_date}' AND '{end_date}'"

        # Initial offset for the API query
        offset = 0
        while True:
            # Get the next 2000 results
            api_response = client.get("a9pz-ixz5", limit=2000, offset=offset, where=where_clause)
            # Break if no more results are returned
            if not api_response:
                break
            # Add the results to the container
            all_results.extend(api_response)
            # Increment the offset to get the next 2000 results
            offset += 2000

        # Format the results for a JSON response
        results = {"results": []}
        for result in all_results:
            results["results"].append({
                'borough': result['boro_nm'].capitalize(),
                'time': result['cmplnt_fr_tm'],
                'date': datetime.strptime(result['cmplnt_fr_dt'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%Y'),
                'latitude': result['latitude'],
                'longitude': result['longitude'],
            })

        return results

    

