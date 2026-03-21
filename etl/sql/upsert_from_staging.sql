insert into weather_hourly (ts, temperature_c, precipitation_mm, windspeed_kmh, source_fetched_at)
select distinct on (ts) ts, temperature_c, precipitation_mm, windspeed_kmh, source_fetched_at
from stg_weather_hourly
order by ts, source_fetched_at desc
on conflict (ts) do update
set temperature_c = excluded.temperature_c,
    precipitation_mm = excluded.precipitation_mm,
    windspeed_kmh = excluded.windspeed_kmh,
    source_fetched_at = excluded.source_fetched_at;

truncate table stg_weather_hourly;