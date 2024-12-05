from app import App


db_path = "../db/data.db"


if __name__ == "__main__":
    App = App(db_path)
    # App.generate_coordinates(4)
    # App.mark_points()
    App.build_routes()
    App.build_corridor(1000)
    App.show_map()
    # App.db.clear_base()
    App.db.close()
