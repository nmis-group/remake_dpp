/* nav.js — open-dpp shared navigation
   Drop this file in the repo root.
   Each page needs: <div id="topbar" class="topbar"></div>
   followed by:     <script src="nav.js"></script> (or ../../nav.js for deep pages) */

(function () {
  var path = window.location.pathname;

  // Pages in /schemas/textile/ need ../../ to reach the root
  var root = (path.indexOf('/schemas/textile/') !== -1) ? '../../' : '';

  // Detect current page for active link
  var isTracker = path.endsWith('tracker.html');
  var isSchema  = path.endsWith('schema.html');
  var isMatrix  = path.endsWith('responsibility_matrix.html');

  // Pills — only on schema and matrix, populated by each page's own JS
  var pills = (isSchema || isMatrix)
    ? '<div class="topbar-right">'
    +   '<span class="pill" id="hd-version"></span>'
    +   '<span class="pill pill-draft" id="hd-status"></span>'
    + '</div>'
    : '';

  function a(href, label, active) {
    return '<a class="topbar-link' + (active ? ' current' : '') + '" href="' + root + href + '">' + label + '</a>';
  }

  var html
    = '<div class="w">'
    +   '<a class="topbar-title" href="' + root + 'index.html" style="text-decoration:none;color:#fff;">open-dpp</a>'
    +   '<nav class="topbar-nav">'
    +     a('tracker.html',                               'Legislation tracker',  isTracker)
    +     a('schemas/textile/schema.html',                'Textile schema',       isSchema)
    +     a('schemas/textile/responsibility_matrix.html', 'Responsibility matrix', isMatrix)
    +   '</nav>'
    +   pills
    + '</div>';

  var el = document.getElementById('topbar');
  if (el) { el.innerHTML = html; }
}());
