-- Suscripciones Gratuito/Premium: el plan pasa a ser POR USUARIO.
-- Antes vivia en organizaciones (es_premium) y toda la organizacion lo
-- heredaba; ahora cada usuario contrata y mantiene su propio plan.
-- 0 = gratuito, 1 = premium.

-- 1. Columnas del plan en la tabla usuarios.
ALTER TABLE usuarios
  ADD COLUMN es_premium TINYINT(1) NOT NULL DEFAULT 0 AFTER password_hash,
  ADD COLUMN fecha_premium TIMESTAMP NULL AFTER es_premium;

-- 2. Migrar el plan actual: quien heredaba premium de su organizacion
--    conserva el plan como usuario propio.
UPDATE usuarios u
  JOIN organizaciones o ON o.id_organizacion = u.id_organizacion
  SET u.es_premium = o.es_premium,
      u.fecha_premium = o.fecha_premium
  WHERE o.es_premium = 1;

-- 3. Las columnas de organizaciones quedan obsoletas: se retiran para que
--    no exista un segundo lugar donde "viva" el plan.
ALTER TABLE organizaciones
  DROP COLUMN es_premium,
  DROP COLUMN fecha_premium;
