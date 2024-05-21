/**
 * Constructs and returns a function that, when called, resizes the current
 * iframes to match its contents. The function is debounced.
 *
 * @param {String} site - The base URL of the site.
 * @param {String} frameId - The last segment of the URL of the interwiki
 * iframe, used by Wikidot to identify it when resizing it.
 * @param {Number=} [debounceTime] - Debounce delay to stagger repeated calls to the resizer. Defaults to 750 ms.
 * @returns {((height: Number=) => void)}
 */
function createResizeIframe(site, frameId, debounceTime) {
  if (debounceTime == null) debounceTime = 750
  let container = document.getElementById("resizer-container")
  if (container == null) {
    container = document.createElement("div")
    container.id = "resizer-container"
    document.body.appendChild(container)
  }
  const resizer = document.createElement("iframe")
  resizer.style.display = "none"
  container.appendChild(resizer)

  // Prefix frame ID with leading slash, required for resize-iframe.html
  if (frameId[0] !== "/") frameId = "/" + frameId

  return debounce((height) => {
    if (height == null) {
      // Measure from the top of the document to the iframe container to get
      // the document height - this takes into account inner margins, unlike
      // e.g. document.body.clientHeight
      // The container must not have display:none for this to work, which is
      // why the iframe has it instead
      let height = container.getBoundingClientRect().top
      // Brute-force past any subpixel issues
      if (height) height += 1
    }

    resizer.src = `${site}/common--javascript/resize-iframe.html?#${height}${frameId}`
  }, debounceTime)
}

/**
 * Automatically constructs a resizer and makes some reasonable guesses
 * about when to activate it.
 *
 * @param {String} site 
 * @param {String} frameId 
 */
function autoResizeIframe(site) {
  const frameId = location.href.replace(/^.*\//, "/")
  const resize = createResizeIframe(site, frameId)
  const observer = new ResizeObserver(() => resize())
  observer.observe(document.documentElement)
}

/**
 * Debounces a function, delaying its execution until a certain amount of
 * time has passed since the last time it was called, and aggregating all
 * calls made in that time into one.
 *
 * @param {Function} func - The function to call.
 * @param {Number} wait - The number of milliseconds to wait after any call
 * to the debounced function before executing it.
 * @returns {Function} The debounced function
 */
function debounce(func, wait) {
  let timeout = 0
  return () => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(arguments), wait)
  }
}