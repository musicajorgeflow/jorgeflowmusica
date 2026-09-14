// Service worker de JorgeFlow Música.
//
// SOLO cachea el "esqueleto" de la app (HTML, CSS, JS e iconos) para que
// abra al instante y se pueda instalar como app. Pesa unos pocos KB en
// total, nada comparado con el tamaño de las canciones.
//
// A PROPOSITO no cachea nada de audio, portadas ni library.json: esos
// siguen pidiendose siempre a internet tal cual, igual que hasta ahora.
// Asi nunca ocupa espacio de mas ni sirve canciones/listas desactualizadas.
//
// IMPORTANTE: cada vez que cambies index.html, style.css o script.js de
// forma notable, sube en uno el numero de CACHE_VERSION de abajo. Si no,
// el service worker seguira sirviendo el "esqueleto" (no las canciones,
// esas siempre van directas a la red) de la version vieja mientras se
// actualiza en segundo plano, y el cambio tardara una recarga extra en
// notarse. Subir el numero fuerza a que se note al momento.
const CACHE_VERSION = 1;
const CACHE_NAME = `jorgeflow-shell-v${CACHE_VERSION}`;

const SHELL_FILES = [
  "./",
  "./index.html",
  "./style.css",
  "./script.js",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name.startsWith("jorgeflow-shell-") && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Solo tocamos peticiones GET a nuestro propio origen. Cualquier otra
  // cosa (audio de R2/Supabase, portadas, library.json, peticiones a
  // otros dominios) pasa de largo tal cual, nunca se cachea.
  if (req.method !== "GET" || url.origin !== self.location.origin) return;

  const esEsqueleto = SHELL_FILES.some(
    (f) => url.pathname.endsWith(f.replace("./", "/")) || (f === "./" && url.pathname === "/")
  );
  if (!esEsqueleto) return; // deja pasar library.json y todo lo demas sin tocar

  // Stale-while-revalidate: responde al instante con lo que haya en cache
  // (carga rapida) y, en paralelo, pide la version nueva a la red para
  // que la SIGUIENTE vez ya este actualizada.
  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(req);
      const network = fetch(req)
        .then((res) => {
          if (res.ok) cache.put(req, res.clone());
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
