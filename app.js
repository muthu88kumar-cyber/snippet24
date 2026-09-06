(() => {
  "use strict";

  const state = {
    stories: [],
    category: "All",
    speed: 10,
    lang: localStorage.getItem("snippet24_lang") || "en",
    location: JSON.parse(
      localStorage.getItem("snippet24_location") || "null"
    )
  };

  const $ = selector => document.querySelector(selector);

  const $$ = selector =>
    [...document.querySelectorAll(selector)];

  const esc = value =>
    String(value ?? "").replace(
      /[&<>"']/g,
      character =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;"
        })[character]
    );


  /* =========================================================
     ARTICLE HELPERS
     ========================================================= */

  function titleOf(story) {
    return (
      story?.translations?.[state.lang]?.title ||
      story?.[state.lang]?.title ||
      story?.title ||
      story?.headline ||
      ""
    );
  }

  function summaryOf(story) {
    return (
      story?.translations?.[state.lang]?.summary ||
      story?.[state.lang]?.summary ||
      story?.summary ||
      ""
    );
  }

  function pointsOf(story) {
    return (
      story?.translations?.[state.lang]?.key_points ||
      story?.[state.lang]?.key_points ||
      story?.key_points ||
      story?.snippet_lines ||
      []
    );
  }

  function imageOf(story) {
    return (
      story?.ai_image_url ||
      story?.image ||
      story?.image_url ||
      story?.ai_image ||
      ""
    );
  }

  function sourceOf(story) {
    return (
      story?.source_url ||
      story?.original_source_url ||
      story?.original_url ||
      story?.url ||
      ""
    );
  }

  function categoryOf(story) {
    const raw =
      story?.category ||
      story?.section ||
      "India";

    if (raw === "In India") {
      return "India";
    }

    return raw;
  }

  function hasTranslation(story) {
    return (
      state.lang === "en" ||
      !!(
        story?.translations?.[state.lang] ||
        story?.[state.lang]
      )
    );
  }


  /* =========================================================
     LOCATION
     ========================================================= */

  function storyLocation(story) {

    const location =
      story?.location ||
      story?.geo ||
      {};

    return {
      country: String(location.country || "").toLowerCase(),
      state: String(location.state || "").toLowerCase(),
      district: String(location.district || "").toLowerCase(),
      city: String(
        location.city ||
        location.town ||
        ""
      ).toLowerCase(),

      taluk: String(
        location.taluk ||
        location.block ||
        ""
      ).toLowerCase(),

      locality: String(
        location.locality ||
        location.village ||
        location.ward ||
        ""
      ).toLowerCase()
    };
  }


  function locationScore(story) {

    if (!state.location) {
      return 0;
    }

    const storyLoc =
      storyLocation(story);

    const userLoc =
      Object.fromEntries(
        Object.entries(state.location).map(
          ([key, value]) => [
            key,
            String(value || "").toLowerCase()
          ]
        )
      );

    let score = 0;

    if (
      userLoc.locality &&
      storyLoc.locality &&
      userLoc.locality === storyLoc.locality
    ) {
      score += 120;
    }

    if (
      userLoc.taluk &&
      storyLoc.taluk &&
      userLoc.taluk === storyLoc.taluk
    ) {
      score += 95;
    }

    if (
      userLoc.city &&
      storyLoc.city &&
      userLoc.city === storyLoc.city
    ) {
      score += 75;
    }

    if (
      userLoc.district &&
      storyLoc.district &&
      userLoc.district === storyLoc.district
    ) {
      score += 55;
    }

    if (
      userLoc.state &&
      storyLoc.state &&
      userLoc.state === storyLoc.state
    ) {
      score += 30;
    }

    return score;
  }


  function importanceScore(story) {

    return (
      {
        CRITICAL: 80,
        HIGH: 50,
        MEDIUM: 20,
        LOW: 5
      }[
        String(
          story?.importance || ""
        ).toUpperCase()
      ] || 10
    );
  }


  function freshnessScore(story) {

    const time = Date.parse(
      story?.published_at ||
      story?.updated_at ||
      ""
    );

    if (!Number.isFinite(time)) {
      return 0;
    }

    return Math.max(
      0,
      40 -
        (Date.now() - time) /
          3600000
    );
  }


  function filtered() {

    return state.stories
      .filter(hasTranslation)
      .filter(
        story =>
          state.category === "All" ||
          categoryOf(story) ===
            state.category
      )
      .sort(
        (a, b) =>
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


  /* =========================================================
     STORIES
     ========================================================= */

  async function loadStories() {

    setStatus(
      "Finding the signal…"
    );

    let data = null;

    try {

      const response =
        await fetch(
          "./api/stories",
          {
            cache: "no-store"
          }
        );

      if (response.ok) {
        data = await response.json();
      }

    } catch (_) {}


    if (!data) {

      try {

        const response =
          await fetch(
            "./articles.json",
            {
              cache: "no-store"
            }
          );

        if (response.ok) {
          data =
            await response.json();
        }

      } catch (_) {}

    }


    if (Array.isArray(data)) {

      state.stories = data;

    } else if (
      Array.isArray(data?.stories)
    ) {

      state.stories =
        data.stories;

    } else if (
      Array.isArray(data?.articles)
    ) {

      state.stories =
        data.articles;

    } else {

      state.stories = [];

    }

    render();
  }


  function setStatus(text) {

    const element =
      $("#status");

    if (element) {
      element.textContent = text;
    }
  }


  function render() {

    const stories =
      filtered();

    renderHeroStories(stories);

    renderMoreStories(stories);

    renderTicker(stories);

    renderCounts();

    syncControls();

    setStatus(
      stories.length
        ? `${stories.length} stories • updated now`
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
      stories.slice(1, 4);


    if (!first) {

      box.innerHTML = `
        <article class="lead-story">
          <div class="lead-copy">

            <span class="signal">
              WAITING FOR SIGNAL
            </span>

            <h3>
              Your most important stories
              will appear here.
            </h3>

            <p>
              Publish stories to
              articles.json or connect
              the /api/stories feed.
            </p>

          </div>
        </article>

        <div class="side-stories">

          <div class="side-card">

            <div class="story-image"></div>

            <div>
              <h3>
                More stories will appear
                as the feed grows.
              </h3>

              <small>
                FAST NEWS • REAL IMPACT
              </small>
            </div>

          </div>

        </div>
      `;

      return;
    }


    const image =
      imageOf(first);

    const imageTag =
      image
        ? `
          <img
            src="${esc(image)}"
            alt=""
            loading="eager"
            onerror="this.remove()"
          >
        `
        : "";


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
              pointsOf(first)
                .slice(0, 2)
                .join(" • ") ||
              "The latest important development, explained simply."
            )}
          </p>

          <div class="lead-meta">

            ${esc(
              categoryOf(first)
            )}

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
                    More stories will appear
                    as the feed grows.
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


  function sideCard(story) {

    const image =
      imageOf(story);

    return `

      <article class="side-card">

        ${
          image
            ? `
              <img
                src="${esc(image)}"
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
              story.signal ||
              categoryOf(story)
            )}
          </span>

          <h3>
            ${esc(
              titleOf(story) ||
              "Story title unavailable"
            )}
          </h3>

          <small>
            ${esc(
              categoryOf(story)
            )}
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
      stories.slice(0, 8);


    if (!items.length) {

      box.innerHTML = `
        <div class="story-row">

          <div></div>

          <div>

            <h3>
              No stories found yet.
            </h3>

            <p>
              Connect the news feed
              to start publishing.
            </p>

          </div>

        </div>
      `;

      return;
    }


    box.innerHTML =
      items
        .map(story => {

          const image =
            imageOf(story);

          const source =
            sourceOf(story);

          const body = `

            ${
              image
                ? `
                  <img
                    src="${esc(image)}"
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
                  titleOf(story) ||
                  "Story title unavailable"
                )}
              </h3>

              <p>
                ${esc(
                  summaryOf(story) ||
                  pointsOf(story)[0] ||
                  "Understand what happened and why it matters."
                )}
              </p>

            </div>

            <span class="go">
              ›
            </span>
          `;


          if (source) {

            return `
              <a
                class="story-row"
                href="${esc(source)}"
                target="_blank"
                rel="noopener noreferrer"
              >
                ${body}
              </a>
            `;

          }


          return `
            <div class="story-row">
              ${body}
            </div>
          `;

        })
        .join("");
  }


  function renderTicker(stories) {

    const element =
      $("#tickerTrack");

    if (!element) {
      return;
    }

    const items =
      stories.slice(0, 10);


    if (!items.length) {

      element.innerHTML = `
        <span>
          <strong>●</strong>
          Waiting for the latest
          Snippet24 signal…
        </span>
      `;

      return;
    }


    const line =
      items
        .map(
          story => `
            <span>
              <strong>●</strong>
              ${esc(
                titleOf(story)
              )}
            </span>
          `
        )
        .join("");


    element.innerHTML =
      line + line;
  }


  /* =========================================================
     AROUND YOU
     ========================================================= */

  function renderCounts() {

    const relevant =
      state.stories
        .filter(hasTranslation);


    const near =
      relevant.filter(
        story =>
          locationScore(story) >= 70
      ).length;


    const district =
      relevant.filter(
        story =>
          locationScore(story) >= 55
      ).length;


    const stateCount =
      relevant.filter(
        story =>
          locationScore(story) >= 30
      ).length;


    const india =
      relevant.filter(
        story =>
          categoryOf(story) ===
          "India"
      ).length;


    const global =
      relevant.filter(
        story =>
          categoryOf(story) ===
          "Global"
      ).length;


    const location =
      state.location;


    $("#aroundLocationName").textContent =
      location
        ? (
            location.locality ||
            location.city ||
            location.district ||
            location.state ||
            "Your location"
          )
        : "Location unavailable";


    $("#aroundLocationDetail").textContent =
      location
        ? [
            location.district,
            location.state
          ]
            .filter(Boolean)
            .join(" • ")
        : "Allow location access to personalize local news";


    $("#nearCount").textContent =
      location ? near : "—";

    $("#districtCount").textContent =
      location ? district : "—";

    $("#stateCount").textContent =
      location ? stateCount : "—";

    $("#indiaCount").textContent =
      india;

    $("#globalCount").textContent =
      global;
  }


  /* =========================================================
     CONTROLS
     ========================================================= */

  function syncControls() {

    $$("[data-category]")
      .forEach(element => {

        element.classList.toggle(
          "active",
          element.dataset.category ===
            state.category
        );

      });


    $$("[data-speed]")
      .forEach(element => {

        element.classList.toggle(
          "active",
          Number(
            element.dataset.speed
          ) === state.speed
        );

      });
  }


  function setCategory(category) {

    state.category =
      category;

    render();

    $("#stories")?.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }


  /* =========================================================
     SEARCH
     ========================================================= */

  function openSearch() {

    const overlay =
      $("#searchOverlay");

    if (!overlay) {
      return;
    }

    overlay.hidden = false;

    overlay.setAttribute(
      "aria-hidden",
      "false"
    );

    document.body.classList.add(
      "search-open"
    );

    setTimeout(
      () =>
        $("#searchInput")?.focus(),
      50
    );
  }


  function closeSearch() {

    const overlay =
      $("#searchOverlay");

    if (!overlay) {
      return;
    }

    overlay.hidden = true;

    overlay.setAttribute(
      "aria-hidden",
      "true"
    );

    document.body.classList.remove(
      "search-open"
    );
  }


  function runSearch(query) {

    const box =
      $("#searchResults");

    if (!box) {
      return;
    }

    const q =
      query.trim().toLowerCase();


    if (!q) {

      box.innerHTML = "";

      return;
    }


    const results =
      state.stories
        .filter(story =>
          [
            titleOf(story),
            summaryOf(story),
            ...(pointsOf(story) || []),
            categoryOf(story),
            JSON.stringify(
              story?.location || {}
            )
          ]
            .join(" ")
            .toLowerCase()
            .includes(q)
        )
        .slice(0, 10);


    box.innerHTML =
      results.length

        ? results
            .map(story => {

              const source =
                sourceOf(story);

              const html = `

                <strong>
                  ${esc(
                    titleOf(story)
                  )}
                </strong>

                <br>

                <small>
                  ${esc(
                    categoryOf(story)
                  )}
                </small>
              `;


              if (source) {

                return `
                  <a
                    class="search-result"
                    href="${esc(source)}"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    ${html}
                  </a>
                `;
              }


              return `
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


  /* =========================================================
     LOCATION MODAL
     ========================================================= */

  /*
   * IMPORTANT:
   *
   * openLocationModal() is ONLY called by:
   *
   * #changeLocationBtn
   *
   * It is NEVER called during startup.
   */

  function openLocationModal() {

    const modal =
      $("#locationModal");

    if (!modal) {
      return;
    }


    const location =
      state.location || {};


    $("#manualState").value =
      location.state || "";

    $("#manualDistrict").value =
      location.district || "";

    $("#manualCity").value =
      location.city || "";

    $("#manualTaluk").value =
      location.taluk || "";

    $("#manualLocality").value =
      location.locality || "";


    modal.hidden = false;

    modal.setAttribute(
      "aria-hidden",
      "false"
    );

    document.body.classList.add(
      "location-open"
    );
  }


  function closeLocationModal() {

    const modal =
      $("#locationModal");

    if (!modal) {
      return;
    }


    modal.hidden = true;

    modal.setAttribute(
      "aria-hidden",
      "true"
    );

    document.body.classList.remove(
      "location-open"
    );
  }


  function saveManualLocation() {

    const location = {

      country: "India",

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

      source: "manual"
    };


    state.location =
      location;


    localStorage.setItem(
      "snippet24_location",
      JSON.stringify(location)
    );


    closeLocationModal();

    updateHeaderWeatherFromLocation();

    render();
  }


  /* =========================================================
     REVERSE GEOCODING
     ========================================================= */

  async function reverseGeocode(
    latitude,
    longitude
  ) {

    const url =
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}&localityLanguage=en`;


    const response =
      await fetch(url);


    if (!response.ok) {
      throw new Error(
        "Reverse geocoding failed"
      );
    }


    const data =
      await response.json();


    const address =
      data.address || {};


    const administrative =
      address
        .localityInfo
        ?.administrative ||
      [];


    const district =
      administrative.find(
        item =>
          /district/i.test(
            item.description || ""
          )
      )?.name ||
      address.locality ||
      address.county ||
      "";


    return {

      country:
        address.countryName ||
        data.countryName ||
        "India",

      state:
        address.principalSubdivision ||
        "",

      district,

      city:
        address.city ||
        address.locality ||
        "",

      taluk:
        address.suburb ||
        address.district ||
        "",

      locality:
        address.village ||
        address.locality ||
        address.quarter ||
        "",

      source: "gps",

      lat: latitude,

      lon: longitude
    };
  }


  /* =========================================================
     WEATHER
     ========================================================= */

  function weatherText(code) {

    if (code === 0)
      return ["☀️", "Clear"];

    if ([1, 2].includes(code))
      return ["🌤️", "Partly cloudy"];

    if (code === 3)
      return ["☁️", "Cloudy"];

    if ([45, 48].includes(code))
      return ["🌫️", "Foggy"];

    if (
      [51, 53, 55, 56, 57]
        .includes(code)
    )
      return ["🌦️", "Drizzle"];

    if (
      [61, 63, 65, 66, 67, 80, 81, 82]
        .includes(code)
    )
      return ["🌧️", "Rain"];

    if (
      [71, 73, 75, 77, 85, 86]
        .includes(code)
    )
      return ["🌨️", "Snow"];

    if (
      [95, 96, 99]
        .includes(code)
    )
      return ["⛈️", "Thunderstorm"];

    return ["🌤️", "Weather"];
  }


  async function loadWeather(
    latitude,
    longitude,
    place
  ) {

    try {

      const url =
        `https://api.open-meteo.com/v1/forecast?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1`;


      const response =
        await fetch(url);


      if (!response.ok) {
        throw new Error(
          "Weather failed"
        );
      }


      const data =
        await response.json();


      const [
        icon,
        condition
      ] =
        weatherText(
          data.current
            ?.weather_code
        );


      const temperature =
        Math.round(
          data.current
            ?.temperature_2m
        );


      const high =
        Math.round(
          data.daily
            ?.temperature_2m_max?.[0]
        );


      const low =
        Math.round(
          data.daily
            ?.temperature_2m_min?.[0]
        );


      $("#weatherIcon")
        .textContent =
        icon;


      $("#weatherTemp")
        .textContent =
        Number.isFinite(
          temperature
        )
          ? `${temperature}°`
          : "--°";


      $("#weatherLocation")
        .textContent =
        place ||
        "Your location";


      $("#weatherCondition")
        .textContent =
        `${condition}${
          Number.isFinite(high)
            ? `  H:${high}°`
            : ""
        }${
          Number.isFinite(low)
            ? `  L:${low}°`
            : ""
        }`;

    } catch (_) {

      $("#weatherIcon")
        .textContent =
        "🌤️";

      $("#weatherTemp")
        .textContent =
        "--°";

      $("#weatherCondition")
        .textContent =
        "Weather unavailable";
    }
  }


  async function updateHeaderWeatherFromLocation() {

    const location =
      state.location;


    if (!location) {

      $("#weatherIcon")
        .textContent =
        "📍";

      $("#weatherTemp")
        .textContent =
        "--°";

      $("#weatherLocation")
        .textContent =
        "Location unavailable";

      $("#weatherCondition")
        .textContent =
        "Weather unavailable";

      return;
    }


    const place =
      location.city ||
      location.locality ||
      location.district ||
      location.state ||
      "Your location";


    $("#weatherLocation")
      .textContent =
      place;


    $("#weatherCondition")
      .textContent =
      "Updating weather…";


    if (
      Number.isFinite(
        Number(location.lat)
      ) &&
      Number.isFinite(
        Number(location.lon)
      )
    ) {

      await loadWeather(
        Number(location.lat),
        Number(location.lon),
        place
      );

    } else {

      $("#weatherIcon")
        .textContent =
        "📍";

      $("#weatherTemp")
        .textContent =
        "--°";

      $("#weatherCondition")
        .textContent =
        "Location saved";
    }
  }


  /* =========================================================
     AUTOMATIC LOCATION
     ========================================================= */

  function detectLocationSilently() {

    /*
     * THIS FUNCTION ONLY DETECTS LOCATION.
     *
     * It NEVER opens the location modal.
     */

    if (
      !navigator.geolocation
    ) {

      setLocationUnavailable();

      return;
    }


    navigator.geolocation.getCurrentPosition(

      async position => {

        try {

          const location =
            await reverseGeocode(
              position.coords.latitude,
              position.coords.longitude
            );


          state.location =
            location;


          localStorage.setItem(
            "snippet24_location",
            JSON.stringify(location)
          );


          render();

          await loadWeather(
            location.lat,
            location.lon,
            location.city ||
            location.locality ||
            location.district ||
            location.state ||
            "Your location"
          );

        } catch (_) {

          setLocationUnavailable();
        }
      },


      () => {

        /*
         * Permission denied:
         * continue normally.
         * NO POPUP.
         */

        setLocationUnavailable();
      },


      {
        enableHighAccuracy: false,
        timeout: 9000,
        maximumAge: 3600000
      }
    );
  }


  function setLocationUnavailable() {

    $("#weatherIcon")
      .textContent =
      "📍";

    $("#weatherTemp")
      .textContent =
      "--°";

    $("#weatherLocation")
      .textContent =
      "Location unavailable";

    $("#weatherCondition")
      .textContent =
      "Tap Change if you want to set it";

    renderCounts();
  }


  /* =========================================================
     EVENT HANDLERS
     ========================================================= */

  $$("[data-category]")
    .forEach(element => {

      element.addEventListener(
        "click",
        () => {

          if (
            element.dataset.category
          ) {

            setCategory(
              element.dataset.category
            );
          }
        }
      );

    });


  $$("[data-speed]")
    .forEach(element => {

      element.addEventListener(
        "click",
        () => {

          state.speed =
            Number(
              element.dataset.speed
            );

          syncControls();
        }
      );

    });


  /* SEARCH */

  $("#searchBtn")
    ?.addEventListener(
      "click",
      openSearch
    );


  $("#searchClose")
    ?.addEventListener(
      "click",
      closeSearch
    );


  $("#searchOverlay")
    ?.addEventListener(
      "click",
      event => {

        if (
          event.target ===
          $("#searchOverlay")
        ) {

          closeSearch();
        }
      }
    );


  $("#searchInput")
    ?.addEventListener(
      "input",
      event =>
        runSearch(
          event.target.value
        )
    );


  /* MENU */

  $("#menuBtn")
    ?.addEventListener(
      "click",
      () => {

        const menu =
          $("#mobileMenu");

        if (!menu) {
          return;
        }

        menu.hidden =
          !menu.hidden;

        $("#menuBtn")
          .setAttribute(
            "aria-expanded",
            String(!menu.hidden)
          );
      }
    );


  /* =========================================================
     LOCATION
     ========================================================= */

  /*
   * THIS IS THE ONLY PLACE THAT OPENS
   * THE LOCATION MODAL.
   */

  $("#changeLocationBtn")
    ?.addEventListener(
      "click",
      openLocationModal
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


  $("#modalUseCurrentBtn")
    ?.addEventListener(
      "click",
      () => {

        closeLocationModal();

        detectLocationSilently();
      }
    );


  /* OTHER */

  $("#worldArrow")
    ?.addEventListener(
      "click",
      () => setCategory("India")
    );


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
            behavior: "smooth",
            block: "start"
          });
      }
    );


  $("#viewAllBtn")
    ?.addEventListener(
      "click",
      () =>
        setCategory("All")
    );


  $("#premiumBtn")
    ?.addEventListener(
      "click",
      () =>
        alert(
          "Snippet24 Premium — Deep Dive, expert perspective, data, context and what happens next."
        )
    );


  /* =========================================================
     STARTUP
     ========================================================= */

  /*
   * CRITICAL:
   *
   * DO NOT CALL openLocationModal() HERE.
   *
   * The modal is forcibly closed on startup.
   */

  const locationModal =
    $("#locationModal");

  if (locationModal) {

    locationModal.hidden = true;

    locationModal.setAttribute(
      "aria-hidden",
      "true"
    );
  }


  document.body.classList.remove(
    "location-open"
  );


  /* Start normal homepage */

  updateHeaderWeatherFromLocation();

  loadStories();


  /*
   * Automatic GPS detection is silent.
   *
   * It does NOT open the modal.
   */

  if (!state.location) {

    setTimeout(
      detectLocationSilently,
      500
    );
  }


  /* ESC closes overlays */

  document.addEventListener(
    "keydown",
    event => {

      if (
        event.key === "Escape"
      ) {

        closeSearch();

        closeLocationModal();
      }
    }
  );

})();