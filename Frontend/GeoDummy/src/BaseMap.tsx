import 'leaflet2/dist/leaflet.css';
function BaseMap(){
    let map = L.map('map').setView([51.505, -0.09], 13);
    return( 
         <div id="map" className="h-[200px]">


         </div>
    )
}

export default BaseMap