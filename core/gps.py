import threading
import time
import math

# Import Windows Location API
try:
    import winsdk.windows.devices.geolocation as wdg
    print(" Windows Location API loaded.")
    WINDOWS_LOCATION_API_AVAILABLE = True
except ImportError:
    print(" winsdk module not found.")
    WINDOWS_LOCATION_API_AVAILABLE = False
except Exception as e:
    print(f" Error loading winsdk: {e}")
    WINDOWS_LOCATION_API_AVAILABLE = False


class GPS:
    MAX_JUMP_THRESHOLD_KM = 2.0

    def __init__(self):
        self.latitude = 0.0
        self.longitude = 0.0
        self.is_running = False
        self._lock = threading.Lock()
        self._geolocator = None
        self._last_known_position = None
        self._total_distance_km = 0.0

    async def _initialize_geolocator(self):
        if WINDOWS_LOCATION_API_AVAILABLE:
            try:
                access_status = await wdg.Geolocator.request_access_async()
                if access_status == wdg.GeolocationAccessStatus.ALLOWED:
                    self._geolocator = wdg.Geolocator()
                    print(" Geolocator initialized.")
                else:
                    print(f" Location access denied: {access_status}")
                    self._geolocator = None
            except Exception as e:
                print(f" Failed to init Geolocator: {e}")
                self._geolocator = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._total_distance_km = 0.0
            self._last_known_position = None

            import asyncio
            def run_async_init():
                asyncio.run(self._initialize_geolocator())

            init_thread = threading.Thread(target=run_async_init, daemon=True)
            init_thread.start()
            init_thread.join(timeout=5)

            threading.Thread(target=self._update_loop, daemon=True).start()
            print("📡 GPS tracking started.")

    def stop(self):
        self.is_running = False
        print(" GPS tracking stopped.")

    def _update_loop(self):
        while self.is_running:
            if self._geolocator and WINDOWS_LOCATION_API_AVAILABLE:
                try:
                    import asyncio
                    async def get_position():
                        try:
                            return await self._geolocator.get_geoposition_async()
                        except Exception as e:
                            print(f" Error getting GPS: {e}")
                            return None

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    position = loop.run_until_complete(get_position())
                    loop.close()

                    if position:
                        new_lat = position.coordinate.latitude
                        new_lon = position.coordinate.longitude

                        with self._lock:
                            if self._last_known_position:
                                prev_lat = self._last_known_position.coordinate.latitude
                                prev_lon = self._last_known_position.coordinate.longitude
                                segment_distance = self._haversine(prev_lat, prev_lon, new_lat, new_lon)

                                # Validasi agar tidak loncat
                                if segment_distance < self.MAX_JUMP_THRESHOLD_KM:
                                    self._total_distance_km += segment_distance
                                    self.latitude = new_lat
                                    self.longitude = new_lon
                                    self._last_known_position = position
                                    print(f" Updated: {self.latitude:.6f}, {self.longitude:.6f} | +{segment_distance:.2f} km | Total: {self._total_distance_km:.2f} km")
                                else:
                                    print(f" Skipped jump: {segment_distance:.2f} km (threshold: {self.MAX_JUMP_THRESHOLD_KM} km)")
                            else:
                                self.latitude = new_lat
                                self.longitude = new_lon
                                self._last_known_position = position
                                print(f"📍 First fix: {self.latitude:.6f}, {self.longitude:.6f}")
                except Exception as e:
                    print(f"❌ Exception in GPS loop: {e}")

            time.sleep(2)

    def get_location(self):
        with self._lock:
            return self.latitude, self.longitude

    def get_total_distance_km(self):
        with self._lock:
            return self._total_distance_km

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c