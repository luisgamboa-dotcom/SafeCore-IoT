-- Suscripciones Gratuito/Premium: el plan pertenece a la organizacion y
-- todos sus usuarios lo heredan. 0 = gratuito, 1 = premium.
ALTER TABLE organizaciones
  ADD COLUMN es_premium TINYINT(1) NOT NULL DEFAULT 0 AFTER activa,
  ADD COLUMN fecha_premium TIMESTAMP NULL AFTER es_premium;
