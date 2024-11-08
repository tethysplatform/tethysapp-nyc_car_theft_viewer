// Custom properties generator for the properties table in the popup window when clicking on boroughs on the map
function customPropertiesGenerator(feature, layer) {
    return "<table class='table table-striped table-bordered table-condensed'>" +
            "<tr><th>Name</th><td>" + feature.A.boro_name + "</td></tr>" +
            "</table>";
}

// Add a legend to the map
function add_legend_map(map) {
    try {
        let legend_element = document.getElementById('legend');
        let control_panel = new ol.control.Control({
            element: legend_element
        });
        map.addControl(control_panel);
    }  
    catch (error) {
        console.error(error);
    }
}

var resultsLayer;
var popupContainer;
var popupOverlay;
var map;

var $searchForm;
var $updateSettingsForm;

var $loadingOverlay;

var $popupContainer;
var $popupContent;

$(document).ready(function() {
    map = TETHYS_MAP_VIEW.getMap();

    add_legend_map(map);

    MAP_LAYOUT.properties_table_generator(customPropertiesGenerator);

    popupContainer = document.getElementById('popup');

    popupOverlay = new ol.Overlay({
        element: popupContainer,
    });
    
    map.addOverlay(popupOverlay)

    // jQuery selectors
    $searchForm = $("#search-form");
    $updateSettingsForm = $("#update-settings-form");

    $loadingOverlay = $("#loading-overlay");

    $popupContainer = $("#popup");
    $popupContent = $("#popup-content");
    
    // Event listeners for form submissions
    $searchForm.submit(function(event) {
        event.preventDefault();
        let formData = new FormData(this);
    
        formData.append('method', "search_form");
        $loadingOverlay.show();
    
        fetch('.', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || "An unknown error occurred.");
                });
            }
            return response.json();
        })
        .then(data => {
            console.log("Search results:");
            console.log(data);
    
            if (data.results.length == 0) {
                TETHYS_APP_BASE.alert("danger", "No results were found with those parameters.");
            } else {
                let resultsPointSource = new ol.source.Vector();
                
                data.results.forEach((result) => {
                    let coords = ol.proj.fromLonLat([result.longitude, result.latitude]);
                    let feature = new ol.Feature({
                        geometry: new ol.geom.Point(coords),
                        borough: result.borough,
                        date: result.date,
                        time: result.time,
                    });
    
                    feature.setStyle(new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 6,
                            fill: new ol.style.Fill({
                                color: result.color
                            })
                        })
                    }));
    
                    resultsPointSource.addFeature(feature);
                });
    
                if (resultsLayer) {
                    map.removeLayer(resultsLayer);
                }
                
                resultsLayer = new ol.layer.Vector({
                    source: resultsPointSource,
                    name: 'search_results_layer',
                });
                
                map.addLayer(resultsLayer);
                
                let $legendDiv = $('#legend');
                
                // Clear the legend div
                $legendDiv.empty(); 

                let legendContentHtml = "<table class='table table-striped table-bordered table-condensed'>" +
                                        "<thead><tr><th colspan='2'>Legend</th></tr></thead>" +
                                        "<tbody>";

                for (let [key, value] of Object.entries(data.legend)) {
                    legendContentHtml += `<tr>
                                            <td><div style='width: 20px; height: 20px; background-color: ${value[0]}; border-radius: 50%;'></div></td>
                                            <td>${key} (${value[1]})</td>
                                            </tr>`;  
                }

                legendContentHtml += "</tbody></table>";

                // Add the legend content to the legend div
                $legendDiv.html(legendContentHtml);  

                // Show the legend div
                $legendDiv.show();
            
            }
        }).catch(error => {
            console.error(error);
            TETHYS_APP_BASE.alert("danger", error.message);
        })
        .finally(() => {
            $loadingOverlay.hide();
        });
    });

    $updateSettingsForm.submit(function(event) {
        event.preventDefault();
        let formData = new FormData(this);

        // Specify the method to handle this POST request
        formData.append('method', "update_settings_form")

        fetch('.', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || "An unknown error occurred.");
                });
            } else {
                TETHYS_APP_BASE.alert("success", "Plot settings updated successfully.");
            }
            return response.json();
        })
        .catch(error => {
            console.error(error);
            TETHYS_APP_BASE.alert("danger", error.message);
        });
    })
    
    // Hover detection
    map.on('pointermove', function (event) {
        map.forEachFeatureAtPixel(event.pixel, function(feature, layer) {
            // If the feature is in the search results layer, populate and show the info popup
            if (layer.get('name') == 'search_results_layer') {
                var properties = feature.getProperties();
                $popupContent.html(`<table class='table table-striped table-bordered table-condensed'>
                                        <tr><th>Borough</th><td>${properties.borough}</td></tr>
                                        <tr><th>Date of Incident</th><td>${properties.date}</td></tr>
                                        <tr><th>Time of Incident</th><td>${properties.time}</td></tr>
                                    </table>`);
                
                $popupContainer.show();
                popupOverlay.setPosition(event.coordinate);
                return true;
            } else {
                // Hide the info popup
                popupOverlay.setPosition(undefined);
                $popupContainer.hide();
            }
        });
        
    });
});
