-- El modelo se consulta con sqlite3 o cualquier cliente compatible con SQLite.
PRAGMA foreign_keys = ON;

-- La energía es sintética: estos totales sirven para comprobar la estructura.
SELECT c.city, d.month, count(*) AS horas,
       round(avg(f.temperature_c), 2) AS temperatura_media_c,
       round(sum(f.energy_kwh), 2) AS energia_sintetica_kwh
FROM fact_hourly f
JOIN dim_city c ON c.city_id=f.city_id
JOIN dim_time t ON t.time_id=f.time_id
JOIN dim_date d ON d.local_date=t.local_date
GROUP BY c.city, d.month
ORDER BY c.city, d.month;

-- Se suma sobre el hecho diario para no multiplicar la radiación por 24.
SELECT c.city, round(sum(s.radiation_kwh_m2_day), 2) AS radiacion_anual_kwh_m2
FROM fact_solar_day s JOIN dim_city c ON c.city_id=s.city_id
GROUP BY c.city ORDER BY c.city;

SELECT count(*) AS filas FROM enriched_data;
PRAGMA foreign_key_check;
PRAGMA integrity_check;
