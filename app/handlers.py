import math
import os
import base64
import numpy as np
import folium
from geopy.distance import geodesic
from scipy.interpolate import splprep, splev
from scgraph.geographs.marnet import marnet_geograph
from functools import lru_cache

# Коррекция долготы для цикличности (если разница больше 180°)
def adjust_coordinates(coordinate_path):
    adjusted_path = [coordinate_path[0]]

    for i in range(1, len(coordinate_path)):
        prev_lat, prev_lon = adjusted_path[-1]
        curr_lat, curr_lon = coordinate_path[i]
        delta_lon = curr_lon - prev_lon

        if delta_lon > 180:
            curr_lon -= 360
        elif delta_lon < -180:
            curr_lon += 360

        adjusted_path.append((curr_lat, curr_lon))
    return adjusted_path


def build_sea_route(start, finish):
    output = marnet_geograph.get_shortest_path(
        origin_node={"latitude": start[0], "longitude": start[1]},
        destination_node={"latitude": finish[0], "longitude": finish[1]}
    )

    coordinate_path = adjust_coordinates(output['coordinate_path'])

    return coordinate_path


def get_circle(points):
    latitudes = [p[0] for p in points]
    longitudes = [p[1] for p in points]
    center = (sum(latitudes) / len(points), sum(longitudes) / len(points))
    radius = max(geodesic(center, point).meters for point in points)

    return center, radius


def shift_polyline(polyline, distance, side="right"):
    def calculate_bearing(lat1, lon1, lat2, lon2):
        """Вычисляет азимут между двумя точками."""
        lat1, lat2 = map(math.radians, [lat1, lat2])
        diff_lon = math.radians(lon2 - lon1)
        x = math.sin(diff_lon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(diff_lon)
        initial_bearing = math.atan2(x, y)
        return (math.degrees(initial_bearing) + 360) % 360

    shifted_polyline = []
    for i in range(len(polyline) - 1):
        # Получаем начальную и конечную точки текущего сегмента
        lat1, lon1 = polyline[i]
        lat2, lon2 = polyline[i + 1]

        # Вычисляем азимут текущего сегмента
        bearing = calculate_bearing(lat1, lon1, lat2, lon2)

        # Определяем направление смещения (±90 градусов от азимута)
        offset_bearing = (bearing + 90) % 360 if side == "right" else (bearing - 90) % 360

        # Смещаем начальную и конечную точки сегмента
        point1_shifted = geodesic(meters=distance).destination((lat1, lon1), offset_bearing)
        point2_shifted = geodesic(meters=distance).destination((lat2, lon2), offset_bearing)

        # Добавляем смещённые точки в новую ломаную
        if i == 0:
            # Первую точку добавляем только один раз
            shifted_polyline.append((point1_shifted.latitude, point1_shifted.longitude))
        shifted_polyline.append((point2_shifted.latitude, point2_shifted.longitude))

    return shifted_polyline


def increase_precision(coordinate_path, n):
    new_path = []
    for i in range(len(coordinate_path) - 1):
        lat1, lon1 = coordinate_path[i]
        lat2, lon2 = coordinate_path[i + 1]
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        # Вычисляем евклидово расстояние в градусах
        distance = (delta_lat ** 2 + delta_lon ** 2) ** 0.5

        # Определяем количество сегментов для разделения
        num_segments = max(int(distance / n), 1)

        for j in range(num_segments):
            fraction = j / num_segments
            new_lat = lat1 + fraction * delta_lat
            new_lon = lon1 + fraction * delta_lon
            new_path.append((new_lat, new_lon))

    # Добавляем последнюю точку
    new_path.append(coordinate_path[-1])
    return new_path


def smooth(coordinates):
    lats, lons = zip(*coordinates)

    # Создаем сплайн-интерполяцию
    tck, u = splprep([lats, lons], s=0.1)
    new_points = splev(np.linspace(0, 1, 100), tck)

    # Преобразуем результат обратно в координаты
    smoothed_coordinates = list(zip(new_points[0], new_points[1]))

    return smoothed_coordinates


def haversine_distance(point1, point2):
    """
    Вычисляет расстояние между двумя точками на сфере (в метрах)
    point1, point2: кортежи (lat, lon)
    """
    R = 6371000  # радиус Земли в метрах

    lat1, lon1 = math.radians(point1[0]), math.radians(point1[1])
    lat2, lon2 = math.radians(point2[0]), math.radians(point2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compare_lines(m, polylines, d):
    for i, line1 in enumerate(polylines):
        for j, line2 in enumerate(polylines):
            if i >= j:
                continue

            border_one = []
            border_two = []

            for idx1, point1 in enumerate(line1):
                for idx2, point2 in enumerate(line2):
                    distance = haversine_distance(point1, point2)

                    if distance <= d:
                        border_one.append((idx1, point1))
                        border_two.append((idx2, point2))

            if border_one and border_two:
                border_one.sort(key=lambda x: x[0])
                border_two.sort(key=lambda x: x[0])

                points_one = [point for idx, point in border_one]
                points_two = [point for idx, point in border_two]

                # Calculate direction vectors
                dir_line1 = np.subtract(points_one[-1], points_one[0])
                dir_line2 = np.subtract(points_two[-1], points_two[0])

                # Compute the dot product to check if they are in the same direction
                dot_product = np.dot(dir_line1, dir_line2)

                if dot_product >= 0:
                    # Lines are in the same direction
                    matching_points = points_one + points_two[::-1]
                else:
                    # Lines are in opposite directions
                    matching_points = points_one + points_two

                if len(matching_points) > 2:
                    folium.Polygon(
                        locations=matching_points,
                        color='yellow',
                        fill=True,
                        fill_color='yellow',
                        fill_opacity=0.4,
                        weight=2
                    ).add_to(m)


@lru_cache(32)
def create_window(whale):
    id, whale_id, type, family_id, photo = whale
    file_path = f"../db/photos/{photo}"

    if os.path.exists(file_path):
        encoded = base64.b64encode(open(file_path, 'rb').read()).decode()

        html = f"""<h3>{type}</h3>
        <img src="data:image/png;base64,{encoded}" width="300px">
        <p>WhaleID: {whale_id}</p>
        <p>FamilyID: {family_id}</p>"""

    else:
        html = f"""<h3>Заголовок</h3>
                <p>Отсутствует фотография</p>
                <p>Описание или дополнительный текст.</p>"""

    return html
