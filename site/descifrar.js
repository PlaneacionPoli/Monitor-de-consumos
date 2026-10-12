/* Descifrado del dashboard estatico (WebCrypto). Compartido por el navegador y Node.
 * Formato: ver scripts/publicar_dashboard.py. Sin servidor: el correo y la
 * contrasena solo derivan una clave local; nada se envia a ninguna parte. */
(function (raiz) {
  const enc = new TextEncoder();
  const dec = new TextDecoder();
  const AAD_DATOS = "monitor-consumos-v1";

  const desdeB64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

  async function sha256Hex(texto, subtle) {
    const h = new Uint8Array(await subtle.digest("SHA-256", enc.encode(texto)));
    return Array.from(h, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  /* Devuelve el objeto de datos o lanza Error("credenciales") sin distinguir si
   * fallo el correo o la contrasena. */
  async function descifrar(blob, correo, contrasena, subtle) {
    subtle = subtle || (raiz.crypto && raiz.crypto.subtle);
    const id = await sha256Hex(correo.trim().toLowerCase(), subtle);
    const usuario = blob.usuarios.find((u) => u.id === id);
    // Con usuario inexistente se gasta el mismo trabajo de derivacion.
    const sal = usuario ? desdeB64(usuario.salt) : new Uint8Array(16);
    const material = await subtle.importKey(
      "raw", enc.encode(contrasena), "PBKDF2", false, ["deriveKey"]);
    const kek = await subtle.deriveKey(
      { name: "PBKDF2", salt: sal, iterations: blob.iter, hash: "SHA-256" },
      material, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    if (!usuario) throw new Error("credenciales");
    let claveDatos;
    try {
      claveDatos = await subtle.decrypt(
        { name: "AES-GCM", iv: desdeB64(usuario.iv), additionalData: enc.encode(id) },
        kek, desdeB64(usuario.key));
    } catch (e) {
      throw new Error("credenciales");
    }
    const k = await subtle.importKey("raw", claveDatos, "AES-GCM", false, ["decrypt"]);
    const claro = await subtle.decrypt(
      { name: "AES-GCM", iv: desdeB64(blob.iv), additionalData: enc.encode(AAD_DATOS) },
      k, desdeB64(blob.data));
    return JSON.parse(dec.decode(claro));
  }

  const api = { descifrar };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Descifrar = api;
})(typeof self !== "undefined" ? self : globalThis);
