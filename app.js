(() => {
  "use strict";

  const state = {
    stories: [],
    category: "All",
    speed: 10,
    location: JSON.parse(
      localStorage.getItem("snippet24_location") || "null"
    )
  };


  const $ = s => document.querySelector(s);

  const $$ = s => [
    ...document.querySelectorAll(s)
  ];


  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      c => ({
        "&":"&amp;",
        "<":"&lt;",
        ">":"&gt;",
        '"':"&quot;",
        "'":"&#39;"
      }[c])
    );


  function titleOf(s) {

    return (
      s?.title ||
      s?.headline ||
      s?.translations?.en?.title ||
      ""
    );

  }


  function summaryOf(s) {

    return (
      s?.summary ||
      s?.translations?.en?.summary ||
      ""
    );

  }


  function pointsOf(s) {

    return (
      s?.key_points ||
      s?.snippet_lines ||
      s?.translations?.en?.key_points ||
      []
    );

  }


  function imageOf(s) {

    return (
      s?.ai_image_url ||
      s?.image ||
      s?.image_url ||
      s?.ai_image ||
      ""
    );

  }


  function sourceOf(s) {

    return (
      s?.source_url ||
      s?.original_source_url ||
      s?.original_url ||
      s?.url ||
      ""
    );

  }


  function categoryOf(s) {

    const raw =
      s?.category ||
      s?.section ||
      "India";

    if (raw === "In India") {
      return "India";
    }

    return raw;

  }


  function storyLocation(s) {

    const l =
      s?.location ||
      s?.geo ||
      {};

    return {

      country:
        String(l.country || "").toLowerCase(),

      state:
        String(l.state || "").toLowerCase(),

      district:
        String(l.district || "").toLowerCase(),

      city:
        String(
          l.city ||
          l.town ||
          ""
        ).toLowerCase(),

      taluk:
        String(
          l.taluk ||
          l.block ||
          ""
        ).toLowerCase(),

      locality:
        String(
          l.locality ||
          l.village ||
          l.ward ||
          ""
        ).toLowerCase()

    };

  }


  function locationScore(s) {

    if (!state.location) {
      return 0;
    }

    const sl =
      storyLocation(s);

    const l =
      Object.fromEntries(
        Object.entries(state.location).map(
          ([k,v]) => [
            k,
            String(v || "").toLowerCase()
          ]
        )
      );

    let score = 0;


    if (
      l.locality &&
      sl.locality &&
      l.locality === sl.locality
    ) {
      score += 120;
    }


    if (
      l.taluk &&
      sl.taluk &&
      l.taluk === sl.taluk
    ) {
      score += 95;
    }


    if (
      l.city &&
      sl.city &&
      l.city === sl.city
    ) {
      score += 75;
    }


    if (
      l.district &&
      sl.district &&
      l.district === sl.district
    ) {
      score += 55;
    }


    if (
      l.state &&
      sl.state &&
      l.state === sl.state
    ) {
      score += 30;
    }


    return score;

  }


  function importanceScore(s) {

    const map = {
      CRITICAL:80,
      HIGH:50,
      MEDIUM:20,
      LOW:5
    };

    return (
      map[
        String(
          s?.importance || ""
        ).toUpperCase()
      ] || 10
    );

  }


  function freshnessScore(s) {

    const t =
      Date.parse(
        s?.published_at ||
        s?.updated_at ||
        ""
      );

    if (!Number.isFinite(t)) {
      return 0;
    }

    return Math.max(
      0,
      40 -
      (
        (Date.now() - t) /
        3600000
      )
    );

  }


  function filtered() {

    return state.stories

      .filter(
        s =>
          state.category === "All" ||
          categoryOf(s) === state.category
      )

      .sort(
        (a,b) =>
          (
            locationScore(b) +
            importanceScore(b) +
            freshnessScore(b)
          ) -
          (
            locationScore(a) +
            importanceScore(a) +
            freshnessScore(a)
          )
      );

  }


  async function loadStories() {

    setStatus(
      "Finding the signal…"
    );

    let data = null;


    try {

      const r =
        await fetch(
          "./api/stories",
          {
            cache:"no-store"
          }
        );

      if (r.ok) {
        data = await r.json();
      }

    } catch (_) {}


    if (!data) {

      try {

        const r =
          await fetch(
            "./articles.json",
            {
              cache:"no-store"
            }
          );

        if (r.ok) {
          data = await r.json();
        }

      } catch (_) {}

    }


    if (Array.isArray(data)) {

      state.stories = data;

    } else if (
      Array.isArray(data?.stories)
    ) {

      state.stories = data.stories;

    } else if (
      Array.isArray(data?.articles)
    ) {

      state.stories = data.articles;

    } else {

      state.stories = [];

    }


    render();

  }


  function setStatus(text) {

    const el =
      $("#status");

    if (el) {
      el.textContent = text;
    }

  }


  function render() {

    const all =
      filtered();

    renderHeroStories(all);

    renderMoreStories(all);

    renderTicker(all);

    renderCounts();

    syncControls();


    setStatus(
      all.length
        ? `${all.length} stories • updated now`
        : "No published stories available yet."
    );

  }


  function renderHeroStories(stories) {

    const box =
      $("#topStories");

    if (!box) {
      return;
    }


    const first =
      stories[0];

    const rest =
      stories.slice(1,4);


    if (!first) {

      box.innerHTML = `
        <div class="lead-story">

          <div class="lead-copy">

            <span class="signal">
              WAITING FOR SIGNAL
            </span>

            <h3>
              Your most important stories will appear here.
            </h3>

            <p>
              Publish stories to articles.json
              or connect the /api/stories feed.
            </p>

          </div>

        </div>
      `;

      return;

    }


    const img =
      imageOf(first);


    const imageTag =
      img
        ? `
          <img
            src="${esc(img)}"
            alt=""
            loading="eager"
            onerror="this.remove()"
          >
        `
        : "";


    const pts =
      pointsOf(first)
        .slice(0,3)
        .map(esc)
        .join(" • ");


    const source =
      sourceOf(first);


    box.innerHTML = `

      <article class="lead-story">

        ${imageTag}

        <div class="shade"></div>

        <div class="lead-copy">

          <span class="signal">
            ${esc(
              first.signal ||
              "TOP SIGNAL"
            )}
          </span>

          <h3>
            ${esc(
              titleOf(first) ||
              "Story title unavailable"
            )}
          </h3>

          <p>
            ${esc(
              summaryOf(first) ||
              pts ||
              "The latest important development, explained simply."
            )}
          </p>

          <div class="lead-meta">

            ${esc(categoryOf(first))}

            ${
              first.published_at
                ? " • " +
                  esc(
                    new Date(
                      first.published_at
                    ).toLocaleDateString()
                  )
                : ""
            }

            ${
              source
                ? " • Original source"
                : ""
            }

          </div>

        </div>

      </article>


      <div class="side-stories">

        ${
          rest.length
            ? rest
                .map(sideCard)
                .join("")

            : `

              <div class="side-card">

                <div></div>

                <div>

                  <h3>
                    More stories will appear as the feed grows.
                  </h3>

                  <small>
                    FAST NEWS • REAL IMPACT
                  </small>

                </div>

              </div>

            `
        }

      </div>

    `;

  }


  function sideCard(s) {

    const img =
      imageOf(s);


    return `

      <article class="side-card">

        ${
          img

            ? `
              <img
                src="${esc(img)}"
                alt=""
                loading="lazy"
              >
            `

            : `
              <div class="story-image"></div>
            `
        }


        <div>

          <span class="signal">
            ${esc(
              s.signal ||
              categoryOf(s)
            )}
          </span>

          <h3>
            ${esc(
              titleOf(s) ||
              "Story title unavailable"
            )}
          </h3>

          <small>
            ${esc(categoryOf(s))}
          </small>

        </div>

      </article>

    `;

  }


  function renderMoreStories(stories) {

    const box =
      $("#stories");

    if (!box) {
      return;
    }


    const items =
      stories.slice(0,8);


    box.innerHTML =
      items.length

        ? items.map(s => {

            const img =
              imageOf(s);

            const src =
              sourceOf(s);


            const body = `

              ${
                img

                  ? `
                    <img
                      src="${esc(img)}"
                      alt=""
                      loading="lazy"
                    >
                  `

                  : `
                    <img
                      src=""
                      alt=""
                      aria-hidden="true"
                    >
                  `
              }


              <div>

                <h3>
                  ${esc(
                    titleOf(s) ||
                    "Story title unavailable"
                  )}
                </h3>

                <p>
                  ${esc(
                    summaryOf(s) ||
                    pointsOf(s)[0] ||
                    "Understand what happened and why it matters."
                  )}
                </p>

              </div>


              <span class="go">
                ›
              </span>

            `;


            return src

              ? `
                <a
                  class="story-row"
                  href="${esc(src)}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  ${body}
                </a>
              `

              : `
                <div class="story-row">
                  ${body}
                </div>
              `;

          }).join("")


        : `

          <div class="story-row">

            <div></div>

            <div>

              <h3>
                No stories found yet.
              </h3>

              <p>
                Connect the news feed to start publishing.
              </p>

            </div>

          </div>

        `;

  }


  function renderTicker(stories) {

    const el =
      $("#tickerTrack");

    if (!el) {
      return;
    }


    const items =
      stories.slice(0,10);


    if (!items.length) {

      el.innerHTML = `
        <span>
          <strong>
            LIVE
          </strong>
          Waiting for the latest Snippet24 signal…
        </span>
      `;

      return;

    }


    const line =
      items
        .map(
          s => `
            <span>
              <strong>
                ●
              </strong>

              ${esc(
                titleOf(s)
              )}

            </span>
          `
        )
        .join("");


    el.innerHTML =
      line + line;

  }


  function renderCounts() {

    const relevant =
      state.stories;


    const near =
      relevant.filter(
        s =>
          locationScore(s) >= 70
      ).length;


    const district =
      relevant.filter(
        s =>
          locationScore(s) >= 55
      ).length;


    const stateN =
      relevant.filter(
        s =>
          locationScore(s) >= 30
      ).length;


    const nearEl =
      $("#nearCount");

    const districtEl =
      $("#districtCount");

    const stateEl =
      $("#stateCount");


    if (nearEl) {
      nearEl.textContent =
        state.location
          ? near
          : "—";
    }


    if (districtEl) {
      districtEl.textContent =
        state.location
          ? district
          : "—";
    }


    if (stateEl) {
      stateEl.textContent =
        state.location
          ? stateN
          : "—";
    }

  }


  function syncControls() {

    $$("[data-category]")
      .forEach(
        el =>
          el.classList.toggle(
            "active",
            el.dataset.category ===
            state.category
          )
      );


    $$("[data-speed]")
      .forEach(
        el =>
          el.classList.toggle(
            "active",
            Number(el.dataset.speed) ===
            state.speed
          )
      );

  }


  function setCategory(
    category,
    scroll = true
  ) {

    state.category =
      category;

    render();


    if (scroll) {

      $("#stories")
        ?.scrollIntoView({
          behavior:"smooth",
          block:"start"
        });

    }

  }


  function openSearch() {

    const overlay =
      $("#searchOverlay");

    if (!overlay) {
      return;
    }


    overlay.hidden =
      false;


    setTimeout(
      () =>
        $("#searchInput")
          ?.focus(),
      20
    );

  }


  function runSearch(query) {

    const box =
      $("#searchResults");

    if (!box) {
      return;
    }


    const q =
      query
        .trim()
        .toLowerCase();


    if (!q) {

      box.innerHTML =
        "";

      return;

    }


    const results =
      state.stories
        .filter(s => {

          const hay = [

            titleOf(s),

            summaryOf(s),

            ...(pointsOf(s) || []),

            categoryOf(s)

          ]
            .join(" ")
            .toLowerCase();


          return hay.includes(q);

        })
        .slice(0,10);


    box.innerHTML =

      results.length

        ? results
            .map(s => {

              const src =
                sourceOf(s);


              const html = `

                <strong>
                  ${esc(
                    titleOf(s)
                  )}
                </strong>

                <br>

                <small>
                  ${esc(
                    categoryOf(s)
                  )}
                </small>

              `;


              return src

                ? `
                  <a
                    class="search-result"
                    href="${esc(src)}"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    ${html}
                  </a>
                `

                : `
                  <div class="search-result">
                    ${html}
                  </div>
                `;

            })
            .join("")


        : `
          <div class="search-result">
            No matching story yet.
          </div>
        `;

  }


  function openLocationModal() {

    const l =
      state.location ||
      {};


    $("#manualState").value =
      l.state || "";

    $("#manualDistrict").value =
      l.district || "";

    $("#manualCity").value =
      l.city || "";

    $("#manualTaluk").value =
      l.taluk || "";

    $("#manualLocality").value =
      l.locality || "";


    const modal =
      $("#locationModal");


    modal.hidden =
      false;


    modal.setAttribute(
      "aria-hidden",
      "false"
    );

  }


  function closeLocationModal() {

    const modal =
      $("#locationModal");

    if (!modal) {
      return;
    }


    modal.hidden =
      true;


    modal.setAttribute(
      "aria-hidden",
      "true"
    );

  }


  function saveManualLocation() {

    state.location = {

      country:
        "India",

      state:
        $("#manualState")
          .value
          .trim(),

      district:
        $("#manualDistrict")
          .value
          .trim(),

      city:
        $("#manualCity")
          .value
          .trim(),

      taluk:
        $("#manualTaluk")
          .value
          .trim(),

      locality:
        $("#manualLocality")
          .value
          .trim(),

      source:
        "manual"

    };


    localStorage.setItem(
      "snippet24_location",
      JSON.stringify(
        state.location
      )
    );


    closeLocationModal();

    updateWeather();

    render();

  }


  /*
    SILENT LOCATION DETECTION

    IMPORTANT:
    This NEVER uses navigator.geolocation.
    Therefore it does NOT request
    the iPhone "Allow Location" permission.
  */

  async function detectLocation(
    {
      showModalOnFail = false
    } = {}
  ) {

    setWeatherText(
      "--°",
      "Finding your area",
      "Detecting automatically…",
      "📍"
    );


    try {

      const r =
        await fetch(
          "https://ipapi.co/json/",
          {
            cache:"no-store"
          }
        );


      if (!r.ok) {
        throw new Error(
          "IP location failed"
        );
      }


      const d =
        await r.json();


      const lat =
        Number(d.latitude);

      const lon =
        Number(d.longitude);


      let location = {

        country:
          d.country_name || "",

        state:
          d.region || "",

        district:
          "",

        city:
          d.city || "",

        taluk:
          "",

        locality:
          d.city || "",

        lat:
          Number.isFinite(lat)
            ? lat
            : null,

        lon:
          Number.isFinite(lon)
            ? lon
            : null,

        source:
          "ip"

      };


      /*
        Improve district / town information
        using the approximate IP coordinates.
      */

      if (
        Number.isFinite(lat) &&
        Number.isFinite(lon)
      ) {

        try {

          const g =
            await reverseGeocode(
              lat,
              lon
            );


          location = {

            ...location,

            ...g,

            lat,

            lon,

            source:
              "ip"

          };

        } catch (_) {}

      }


      if (
        !location.city &&
        !location.state
      ) {

        throw new Error(
          "No location name returned"
        );

      }


      state.location =
        location;


      localStorage.setItem(
        "snippet24_location",
        JSON.stringify(
          state.location
        )
      );


      closeLocationModal();


      await updateWeather();


      render();

    }


    catch (_) {

      setWeatherText(
        "--°",
        "Location unavailable",
        "Weather unavailable",
        "📍"
      );


      renderCounts();


      /*
        Automatic startup never opens
        the location popup.

        The popup can only be opened
        when the user taps Change.
      */

      if (showModalOnFail) {
        openLocationModal();
      }

    }

  }


  async function reverseGeocode(
    lat,
    lon
  ) {

    const url =
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${encodeURIComponent(lat)}&longitude=${encodeURIComponent(lon)}&localityLanguage=en`;


    const r =
      await fetch(
        url,
        {
          cache:"no-store"
        }
      );


    if (!r.ok) {
      throw new Error(
        "Reverse geocoding failed"
      );
    }


    const d =
      await r.json();


    const a =
      d.address || {};


    const admin =
      d.localityInfo?.administrative ||
      [];


    const districtItem =
      admin.find(
        x =>
          /district/i.test(
            x.description || ""
          )
      );


    return {

      country:
        a.countryName ||
        d.countryName ||
        "",

      state:
        a.principalSubdivision ||
        "",

      district:
        districtItem?.name ||
        a.locality ||
        "",

      city:
        a.city ||
        a.locality ||
        a.town ||
        a.village ||
        "",

      taluk:
        a.suburb ||
        a.municipality ||
        "",

      locality:
        a.locality ||
        a.village ||
        a.city ||
        a.town ||
        ""

    };

  }


  function weatherDescription(
    code
  ) {

    const c =
      Number(code);


    if (c === 0) {
      return [
        "☀️",
        "Clear"
      ];
    }


    if (
      [1,2].includes(c)
    ) {
      return [
        "🌤️",
        "Partly cloudy"
      ];
    }


    if (c === 3) {
      return [
        "☁️",
        "Cloudy"
      ];
    }


    if (
      [45,48].includes(c)
    ) {
      return [
        "🌫️",
        "Foggy"
      ];
    }


    if (
      [51,53,55,56,57].includes(c)
    ) {
      return [
        "🌦️",
        "Drizzle"
      ];
    }


    if (
      [61,63,65,66,67].includes(c)
    ) {
      return [
        "🌧️",
        "Rain"
      ];
    }


    if (
      [71,73,75,77].includes(c)
    ) {
      return [
        "❄️",
        "Snow"
      ];
    }


    if (
      [80,81,82].includes(c)
    ) {
      return [
        "🌦️",
        "Showers"
      ];
    }


    if (
      [95,96,99].includes(c)
    ) {
      return [
        "⛈️",
        "Thunderstorm"
      ];
    }


    return [
      "🌤️",
      "Weather"
    ];

  }


  function setWeatherText(
    temp,
    place,
    condition,
    icon
  ) {

    if ($("#weatherTemp")) {

      $("#weatherTemp")
        .textContent = temp;

    }


    if ($("#weatherLocation")) {

      $("#weatherLocation")
        .textContent = place;

    }


    if ($("#weatherCondition")) {

      $("#weatherCondition")
        .textContent = condition;

    }


    if ($("#weatherIcon")) {

      $("#weatherIcon")
        .textContent = icon;

    }

  }


  async function updateWeather() {

    const l =
      state.location;


    const place =
      l?.city ||
      l?.locality ||
      l?.state ||
      "Your area";


    if (
      !l?.lat ||
      !l?.lon
    ) {

      setWeatherText(
        "--°",
        place,
        "Weather unavailable",
        "📍"
      );

      return;

    }


    try {

      const url =
        `https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(l.lat)}&longitude=${encodeURIComponent(l.lon)}&current=temperature_2m,weather_code&timezone=auto&forecast_days=1`;


      const r =
        await fetch(
          url,
          {
            cache:"no-store"
          }
        );


      if (!r.ok) {
        throw new Error(
          "Weather failed"
        );
      }


      const d =
        await r.json();


      const [
        icon,
        condition
      ] =
        weatherDescription(
          d.current?.weather_code
        );


      const tempValue =
        Number(
          d.current?.temperature_2m
        );


      const temp =
        Number.isFinite(tempValue)

          ? `${Math.round(tempValue)}°`

          : "--°";


      setWeatherText(
        temp,
        place,
        condition,
        icon
      );

    }


    catch (_) {

      setWeatherText(
        "--°",
        place,
        "Weather unavailable",
        "📍"
      );

    }

  }


  /*
    AROUND YOU

    Local-only.
    India and Global are already
    available in the main navigation.

    The arrow / local buttons show
    location-relevant stories.
  */

  function showLocalNews() {

    const local =
      state.stories

        .filter(
          s =>
            locationScore(s) >= 30
        )

        .sort(
          (a,b) =>
            (
              locationScore(b) +
              freshnessScore(b)
            ) -
            (
              locationScore(a) +
              freshnessScore(a)
            )
        );


    const box =
      $("#stories");


    if (!box) {
      return;
    }


    renderMoreStories(
      local
    );


    setStatus(
      local.length
        ? `${local.length} local stories around you`
        : "No local stories available yet."
    );


    box.scrollIntoView({
      behavior:"smooth",
      block:"start"
    });

  }


  /*
    NAVIGATION
  */

  $$("[data-category]")
    .forEach(
      el =>
        el.addEventListener(
          "click",
          () => {

            if (
              el.dataset.category
            ) {

              setCategory(
                el.dataset.category
              );

            }

          }
        )
    );


  /*
    READING MODES
  */

  $$("[data-speed]")
    .forEach(
      el =>
        el.addEventListener(
          "click",
          () => {

            state.speed =
              Number(
                el.dataset.speed
              );


            syncControls();

          }
        )
    );


  /*
    SEARCH
  */

  $("#searchBtn")
    ?.addEventListener(
      "click",
      openSearch
    );


  $("#searchClose")
    ?.addEventListener(
      "click",
      () => {

        $("#searchOverlay")
          .hidden = true;

      }
    );


  $("#searchInput")
    ?.addEventListener(
      "input",
      e =>
        runSearch(
          e.target.value
        )
    );


  /*
    MOBILE MENU
  */

  $("#menuBtn")
    ?.addEventListener(
      "click",
      () => {

        const m =
          $("#mobileMenu");


        if (!m) {
          return;
        }


        m.hidden =
          !m.hidden;


        $("#menuBtn")
          ?.setAttribute(
            "aria-expanded",
            String(!m.hidden)
          );

      }
    );


  /*
    LOCATION
  */

  $("#changeLocationBtn")
    ?.addEventListener(
      "click",
      openLocationModal
    );


  /*
    AROUND YOU ARROW
  */

  $("#worldArrow")
    ?.addEventListener(
      "click",
      showLocalNews
    );


  $("#nearCard")
    ?.addEventListener(
      "click",
      showLocalNews
    );


  $("#districtCard")
    ?.addEventListener(
      "click",
      showLocalNews
    );


  $("#stateCard")
    ?.addEventListener(
      "click",
      showLocalNews
    );


  $("#locationModalClose")
    ?.addEventListener(
      "click",
      closeLocationModal
    );


  $("#locationModalBackdrop")
    ?.addEventListener(
      "click",
      closeLocationModal
    );


  $("#saveManualLocationBtn")
    ?.addEventListener(
      "click",
      saveManualLocation
    );


  /*
    User can manually request
    automatic detection from the
    Change Location window.

    Still NO browser GPS permission.
  */

  $("#modalUseCurrentBtn")
    ?.addEventListener(
      "click",
      () =>
        detectLocation({
          showModalOnFail:true
        })
    );


  /*
    CATCH ME UP
  */

  $("#catchupBtn")
    ?.addEventListener(
      "click",
      () => {

        state.category =
          "All";

        state.speed =
          60;

        render();


        $("#topStories")
          ?.scrollIntoView({
            behavior:"smooth",
            block:"start"
          });

      }
    );


  /*
    SEE ALL
  */

  $("#viewAllBtn")
    ?.addEventListener(
      "click",
      () =>
        setCategory("All")
    );


  /*
    PREMIUM
  */

  $("#premiumBtn")
    ?.addEventListener(
      "click",
      () =>
        alert(
          "Snippet24 Premium — Deep Dive, expert perspective, data & context, what's next and ad-free reading."
        )
    );


  /*
    STARTUP

    If manual location exists:
      use it.

    Otherwise:
      silently detect approximate
      location using IP.

    NEVER use navigator.geolocation.
  */

  if (state.location) {

    updateWeather();

    renderCounts();

  } else {

    detectLocation();

  }


  /*
    LOAD NEWS
  */

  loadStories();

})();