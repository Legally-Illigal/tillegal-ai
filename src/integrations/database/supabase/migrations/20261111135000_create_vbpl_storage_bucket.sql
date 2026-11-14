INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('vbpl-raw', 'vbpl-raw', FALSE, 104857600)
ON CONFLICT (id) DO NOTHING;
