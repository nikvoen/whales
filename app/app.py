import os
import random
import folium
import webbrowser
import geopandas as gpd
from shapely.geometry import Point

from db import Database
from handlers import shift_polyline, increase_precision, smooth, get_circle, build_sea_route, adjust_coordinates, \
    compare_lines, create_window


def color_change(status):
    if status == 'start':
        return 'blue'
    elif status == 'finish':
        return 'purple'
    else:
        return 'red'


class App:
    def __init__(self, path_db):
        self.routes = []
        self.map_file = None
        self.colors = ['darkred', 'darkblue', 'purple', 'maroon',
                       'navy', 'teal', 'indigo', 'chocolate', 'crimson']
        self.color_key = 0
        self.db = Database(path_db)
        self.ocean_data = gpd.read_file('../assets/ne_50m_ocean.shx')
        self.map = folium.Map(location=[60, 100], zoom_start=3, tiles="Esri.NatGeoWorldMap")

    def generate_coordinates(self, num):
        """Создание фиктивных маршрутов в количестве = num"""
        def is_ocean(lat, lon):
            point = Point(lon, lat)
            return self.ocean_data.contains(point).any()

        def create_water_point():
            lat = random.uniform(0, 80)
            lon = random.uniform(0, 178)

            while not is_ocean(lat, lon):
                lat = random.uniform(0, 80)
                lon = random.uniform(0, 178)

            return lat, lon

        def add_water_points(lat, lon):
            lat_delta = random.uniform(0.01, 0.05)
            lon_delta = random.uniform(0.01, 0.05)

            while not is_ocean(lat + lat_delta, lon + lon_delta):
                lat_delta = random.uniform(0.01, 0.05)
                lon_delta = random.uniform(0.01, 0.05)

            return lat + lat_delta, lon + lon_delta

        for n in range(num):
            num_entries = random.randint(4, 8)  # количество особей
            family_id = random.randint(100, 999)

            for i in range(num_entries):
                whale_id = random.randint(1000, 9999)

                if not self.db.get_whale(whale_id):
                    self.db.insert_whale(whale_id, family_id=family_id)

        families = self.db.get_families()

        for family_id in families:
            whales = self.db.get_family(family_id)

            for record_type in ['start', 'finish']:
                area_lat, area_lon = create_water_point()

                for id_, whale_id, type_, family_id_, photo in whales:
                    lat, lon = add_water_points(area_lat, area_lon)
                    self.db.insert_record(whale_id, record_type, lat, lon)

    def mark_points(self):
        """Отмечает все существующие координаты млекопитающих на карте"""
        all_records = self.db.get_all_records()
        for whales_id, type, latitude, longitude in all_records:
            whale = self.db.get_whale(whales_id)

            window = create_window(whale)
            iframe = folium.IFrame(html=window, width=350, height=350)
            popup = folium.Popup(iframe, max_width=2650)

            icon = folium.Icon(icon='fish-fins', prefix='fa', color=color_change(type))
            folium.Marker(location=[latitude, longitude], popup=popup, icon=icon).add_to(self.map)

            self.map_file = "../output/map.html"
            self.map.save(self.map_file)

    def show_map(self):
        """Открывает карту в стандартном браузере"""
        if self.map_file:
            file_url = "file://" + os.path.abspath(self.map_file)
            webbrowser.open(file_url)
        else:
            print("Карты не существует")

    def build_routes(self):
        """Строит все возможные морские маршруты"""
        families = self.db.get_families()

        for family_id in families:
            start_coords = []
            finish_coords = []
            whales = self.db.get_family(family_id)

            for id_, whale_id, type_, family_id_, photo in whales:
                records = self.db.get_records_by_whale(whale_id)

                for record in records:
                    whales_id, record_type, latitude, longitude = record

                    if record_type == "start":
                        start_coords.append((latitude, longitude))
                    elif record_type == "finish":
                        finish_coords.append((latitude, longitude))

            centers = []
            radiuses = []

            # Добавление окружностей (не учитывает разрыв карты)
            for i in [start_coords, finish_coords]:
                center, radius = get_circle(i)
                centers.append(center)
                radiuses.append(radius)

            radius = max(radiuses)

            # Кратчайший водный маршрут
            coordinate_path = build_sea_route(centers[0], centers[1])

            # Сглаженный мршрут
            smoothed_path = smooth(coordinate_path)

            self.routes.append(smoothed_path)

            shift = radius
            shifted_left = shift_polyline(smoothed_path, distance=shift, side="left")
            shifted_left = adjust_coordinates(shifted_left)
            shifted_right = shift_polyline(smoothed_path, distance=shift, side="right")
            shifted_right = adjust_coordinates(shifted_right)
            zone = shifted_left + shifted_right[::-1]

            folium.Polygon(zone, color=self.colors[self.color_key], fill=True, fill_opacity=0.4).add_to(self.map)

            for center in centers:
                (folium.Circle(location=center,
                               radius=radius,
                               color=self.colors[self.color_key],
                               fill=True,
                               fill_opacity=0.4)
                 .add_to(self.map))

            self.color_key += 1

        self.map_file = "../output/map.html"
        self.map.save(self.map_file)

    def build_corridor(self, width):
        """Строит коридоры движения для существующих маршрутов шириной не более чем width метров"""
        compare_lines(self.map, self.routes, width * 1000)

        self.map_file = "../output/map.html"
        self.map.save(self.map_file)
