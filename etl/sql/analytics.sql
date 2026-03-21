create table if not exists weather_daily (
  date_day timestamp,
  avg_temp_c double precision,
  total_precip_mm double precision,
  avg_windspeed_kmh double precision
);

truncate table weather_daily;
insert into weather_daily
select
  date_trunc('day', ts) as "day",
  avg(temperature_c) as avg_temp_c,
  sum(precipitation_mm) as total_precip_mm,
  avg(windspeed_kmh) as avg_windspeed_kmh
from weather_hourly
group by "day";