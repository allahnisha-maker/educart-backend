CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    image       TEXT NOT NULL DEFAULT '',
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS carts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cart_items (
    cart_id    UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 99),
    PRIMARY KEY (cart_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id            SERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    student_class TEXT NOT NULL,
    address       TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT NOT NULL,
    total         NUMERIC(10, 2) NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
    id         SERIAL PRIMARY KEY,
    order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    price      NUMERIC(10, 2) NOT NULL
);

-- Seed catalogue (same 12 products the frontend shipped with). Re-running is a no-op.
INSERT INTO products (id, name, description, price, image, stock) VALUES
  (1,  'Spiral Notebook',        'A4 ruled notebook with 200 pages of smooth, ink-friendly paper and a sturdy spiral binding.', 120,  '/images/products/notebook.svg',        50),
  (2,  'Gel Pen Set',            'Pack of 10 smooth-writing gel pens in bright colours, with comfortable soft grips.',           199,  '/images/products/gel-pens.svg',        40),
  (3,  'Geometry Box',           'Compass, divider, protractor, set squares, ruler, pencil and eraser in a durable metal case.', 249,  '/images/products/geometry-box.svg',    30),
  (4,  'Scientific Calculator',  '240-function calculator with a two-line display — ideal for maths and science classes.',     1150, '/images/products/calculator.svg',      15),
  (5,  'School Backpack',        'Water-resistant 30 L backpack with padded straps, a front pocket and two side pockets.',      1499, '/images/products/backpack.svg',        20),
  (6,  'Steel Water Bottle',     'Insulated 750 ml bottle that keeps water cold for 12 hours, with a leak-proof lid.',          449,  '/images/products/water-bottle.svg',    35),
  (7,  'Lunch Box',              'BPA-free lunch box with three compartments and a leak-proof, clip-lock lid.',                 399,  '/images/products/lunch-box.svg',       25),
  (8,  'Colour Pencils',         'Set of 24 vibrant, pre-sharpened colour pencils with break-resistant leads.',                 220,  '/images/products/colour-pencils.svg',  45),
  (9,  'Highlighter Set',        'Four pastel highlighters with chisel tips for neat notes and quick revision.',                150,  '/images/products/highlighters.svg',    60),
  (10, 'LED Desk Lamp',          'Adjustable study lamp with three brightness levels and soft, flicker-free light.',            899,  '/images/products/desk-lamp.svg',       10),
  (11, 'World Globe',            '8-inch globe on a sturdy stand — great for geography lessons and homework.',                  699,  '/images/products/globe.svg',           12),
  (12, 'Watercolour Paint Set',  '12 rich watercolour cakes in a tin with a mixing lid and a fine-tip brush.',                  299,  '/images/products/watercolour-set.svg', 30)
ON CONFLICT (id) DO NOTHING;
SELECT setval('products_id_seq', (SELECT max(id) FROM products));
