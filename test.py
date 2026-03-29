import requests
lat = 20.9922113
lon = 105.8147036
api_key = "ok_16ace8365089ab2b0c696a97bc34afc9"
response = requests.get(
    "https://reverse-geocoding-api.omkar.cloud/reverse-geocode",
    params={"lat": lat, "lon": lon},
    headers={"API-Key": api_key}
)
print(response.json())