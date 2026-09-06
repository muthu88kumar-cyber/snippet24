(() => {

  "use strict";


  /* =========================================================
     STATE
  ========================================================= */

  const state = {

    stories: [],

    category: "All",

    speed: 10,

    lang:
      localStorage.getItem("snippet24_lang")
      || "en",

    location:
      JSON.parse(
        localStorage.getItem("snippet24_location")
        || "null"
      ),

    weather: null

  };


  /* =========================================================
     HELPERS
  ========================================================= */

  const $ = selector =>
    document.querySelector(selector);


  const $$ = selector =>
    [...document.querySelectorAll(selector)];


  const escapeHtml = value =>
    String(value ?? "")
      .replace(
        /[&<>"']/g,
        character => ({
          "&":"&amp;",
          "<":"&lt;",
          ">":"&gt;",
          '"':"&quot;",
          "'":"&#39;"
        }[character])
      );


  /* =========================================================
     ARTICLE HELPERS
  ========================================================= */

  function getTitle(story){

    return (

      story?.translations?.[state.lang]?.title ||

      story?.[state.lang]?.title ||

      story?.title ||

      story?.headline ||

      ""

    );

  }


  function getSummary(story){

    return (

      story?.translations?.[state.lang]?.summary ||

      story?.[state.lang]?.summary ||

      story?.summary ||

      ""

    );

  }


  function getPoints(story){

    return (

      story?.translations?.[state.lang]?.key_points ||

      story?.[state.lang]?.key_points ||

      story?.key_points ||

      story?.snippet_lines ||

      []

    );

  }


  function imageOf(story){

    return (

      story?.ai_image_url ||

      story?.image ||

      story?.image_url ||

      story?.ai_image ||

      ""

    );

  }


  function sourceOf(story){

    return (

      story?.source_url ||

      story?.original_source_url ||

      story?.original_url ||

      story?.url ||

      ""

    );

  }


  function categoryOf(story){

    const raw =
      story?.category ||
      story?.section ||
      "India";


    if(raw === "In India")
      return "India";


    if(raw === "Business & Economy")
      return "Business & Economy";


    if(raw === "Tech & AI")
      return "Tech & AI";


    if(raw === "Human & Environment")
      return "Human & Environment";


    return raw;

  }


  function hasTranslation(story){

    return (

      state.lang === "en"

      ||

      !!(
        story?.translations?.[state.lang]

        ||

        story?.[state.lang]
      )

    );

  }


  /* =========================================================
     LOCATION
  ========================================================= */

  function locationText(){

    const l =
      state.location;


    if(!l)
      return "Finding your area";


    return (

      l.locality ||

      l.city ||

      l.town ||

      l.district ||

      l.state ||

      "Your location"

    );

  }


  function locationDetail(){

    const l =
      state.location;


    if(!l)
      return "Understanding your location";


    const parts = [

      l.district,

      l.state

    ].filter(Boolean);


    return parts.length

      ? parts.join(" • ")

      : "Location personalized";

  }


  function normalizeLocation(value){

    return String(
      value || ""
    )
      .trim()
      .toLowerCase();

  }


  function articleLocation(story){

    const l =
      story?.location ||

      story?.geo ||

      {};


    return {

      country:
        normalizeLocation(
          l.country
        ),

      state:
        normalizeLocation(
          l.state
        ),

      district:
        normalizeLocation(
          l.district
        ),

      city:
        normalizeLocation(
          l.city ||
          l.town
        ),

      taluk:
        normalizeLocation(
          l.taluk ||
          l.block
        ),

      locality:
        normalizeLocation(
          l.locality ||
          l.village ||
          l.ward
        )

    };

  }


  function locationScore(story){

    if(!state.location)
      return 0;


    const article =
      articleLocation(story);


    const user = {

      state:
        normalizeLocation(
          state.location.state
        ),

      district:
        normalizeLocation(
          state.location.district
        ),

      city:
        normalizeLocation(
          state.location.city
        ),

      taluk:
        normalizeLocation(
          state.location.taluk
        ),

      locality:
        normalizeLocation(
          state.location.locality
        )

    };


    let score = 0;


    if(
      user.locality &&
      article.locality &&
      user.locality === article.locality
    ){

      score += 120;

    }


    if(
      user.taluk &&
      article.taluk &&
      user.taluk === article.taluk
    ){

      score += 95;

    }


    if(
      user.city &&
      article.city &&
      user.city === article.city
    ){

      score += 75;

    }


    if(
      user.district &&
      article.district &&
      user.district === article.district
    ){

      score += 55;

    }


    if(
      user.state &&
      article.state &&
      user.state === article.state
    ){

      score += 30;

    }


    return score;

  }


  function importanceScore(story){

    const map = {

      CRITICAL:80,

      HIGH:50,

      MEDIUM:20,

      LOW:5

    };


    return (

      map[
        String(
          story?.importance ||
          ""
        ).toUpperCase()
      ]

      || 10

    );

  }


  function freshnessScore(story){

    const timestamp =
      Date.parse(
        story?.published_at ||
        story?.updated_at ||
        ""
      );


    if(
      !Number.isFinite(
        timestamp
      )
    ){

      return 0;

    }


    const hours =
      (
        Date.now() -
        timestamp
      ) / 3600000;


    return Math.max(
      0,
      40 - hours
    );

  }


  /* =========================================================
     FILTER
  ========================================================= */

  function filtered(){

    return state.stories

      .filter(
        hasTranslation
      )

      .filter(
        story =>

          state.category === "All"

          ||

          categoryOf(story)
            ===
          state.category

      )

      .sort(
        (a,b) =>

          (

            locationScore(b)

            +

            importanceScore(b)

            +

            freshnessScore(b)

          )

          -

          (

            locationScore(a)

            +

            importanceScore(a)

            +

            freshnessScore(a)

          )

      );

  }


  /* =========================================================
     LOAD STORIES
  ========================================================= */

  async function loadStories(){

    setStatus(
      "Finding the signal…"
    );


    let data = null;


    try{

      const response =
        await fetch(
          "./api/stories",
          {
            cache:"no-store"
          }
        );


      if(response.ok){

        data =
          await response.json();

      }

    }

    catch(error){

      console.log(
        "API unavailable"
      );

    }


    if(!data){

      try{

        const response =
          await fetch(
            "./articles.json",
            {
              cache:"no-store"
            }
          );


        if(response.ok){

          data =
            await response.json();

        }

      }

      catch(error){

        console.log(
          "articles.json unavailable"
        );

      }

    }


    if(Array.isArray(data)){

      state.stories =
        data;

    }

    else if(
      Array.isArray(
        data?.stories
      )
    ){

      state.stories =
        data.stories;

    }

    else if(
      Array.isArray(
        data?.articles
      )
    ){

      state.stories =
        data.articles;

    }

    else{

      state.stories =
        [];

    }


    render();

  }


  /* =========================================================
     WEATHER
     OPEN-METEO
     NO API KEY REQUIRED
  ========================================================= */

  async function loadWeather(){

    if(
      !state.location?.latitude ||
      !state.location?.longitude
    ){

      return;

    }


    try{

      const latitude =
        state.location.latitude;


      const longitude =
        state.location.longitude;


      const url =

        "https://api.open-meteo.com/v1/forecast"

        +

        "?latitude=" +
        encodeURIComponent(latitude)

        +

        "&longitude=" +
        encodeURIComponent(longitude)

        +

        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"

        +

        "&hourly=precipitation_probability"

        +

        "&timezone=auto";


      const response =
        await fetch(url);


      if(!response.ok)
        throw new Error(
          "Weather unavailable"
        );


      const data =
        await response.json();


      state.weather =
        data;


      renderWeather();

    }

    catch(error){

      console.log(
        "Weather unavailable",
        error
      );

    }

  }


  function weatherDescription(code){

    const descriptions = {

      0:"Clear sky",

      1:"Mainly clear",

      2:"Partly cloudy",

      3:"Overcast",

      45:"Foggy",

      48:"Foggy",

      51:"Light drizzle",

      53:"Drizzle",

      55:"Heavy drizzle",

      61:"Light rain",

      63:"Rain",

      65:"Heavy rain",

      71:"Light snow",

      73:"Snow",

      75:"Heavy snow",

      80:"Rain showers",

      81:"Rain showers",

      82:"Heavy showers",

      95:"Thunderstorm",

      96:"Thunderstorm",

      99:"Thunderstorm"

    };


    return (
      descriptions[code]
      ||
      "Current weather"
    );

  }


  function weatherIcon(code){

    if(code === 0)
      return "☀️";


    if(
      code === 1 ||
      code === 2
    )
      return "⛅";


    if(code === 3)
      return "☁️";


    if(
      code >= 45 &&
      code <= 48
    )
      return "🌫️";


    if(
      code >= 51 &&
      code <= 67
    )
      return "🌧️";


    if(
      code >= 71 &&
      code <= 77
    )
      return "❄️";


    if(
      code >= 80 &&
      code <= 82
    )
      return "🌦️";


    if(code >= 95)
      return "⛈️";


    return "🌤️";

  }


  function renderWeather(){

    const weather =
      state.weather;


    if(
      !weather ||
      !weather.current
    ){

      return;

    }


    const current =
      weather.current;


    const temp =
      Math.round(
        current.temperature_2m
      );


    const feels =
      Math.round(
        current.apparent_temperature
      );


    const wind =
      Math.round(
        current.wind_speed_10m
      );


    const code =
      current.weather_code;


    $("#weatherTemp")
      .textContent =
      `${temp}°`;


    $("#weatherFeels")
      .textContent =
      `${feels}°`;


    $("#weatherCondition")
      .textContent =
      weatherDescription(
        code
      );


    $("#weatherIcon")
      .textContent =
      weatherIcon(
        code
      );


    $("#weatherWind")
      .textContent =
      `${wind} km/h`;


    let rainProbability =
      "--";


    if(
      Array.isArray(
        weather?.hourly?.precipitation_probability
      )
    ){

      const value =
        weather.hourly
          .precipitation_probability[0];


      if(
        Number.isFinite(
          value
        )
      ){

        rainProbability =
          `${value}%`;

      }

    }


    $("#weatherRain")
      .textContent =
      rainProbability;

  }


  /* =========================================================
     RENDER
  ========================================================= */

  function render(){

    const stories =
      filtered();


    renderTopStories(
      stories
    );


    renderMoreStories(
      stories
    );


    renderTicker(
      stories
    );


    renderCounts();


    renderWeather();


    syncControls();


    setStatus(

      stories.length

      ?

      `${stories.length} stories • updated now`

      :

      "No published stories available yet."

    );

  }


  /* =========================================================
     TOP STORIES
  ========================================================= */

  function renderTopStories(
    stories
  ){

    const container =
      $("#topStories");


    if(!container)
      return;


    const first =
      stories[0];


    const rest =
      stories.slice(1,4);


    if(!first){

      container.innerHTML = `

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
              Publish stories to articles.json
              or connect the /api/stories feed.
            </p>

          </div>

        </article>

      `;

      return;

    }


    const image =
      imageOf(first);


    const imageHTML =
      image

      ?

      `

      <img
        src="${escapeHtml(image)}"
        alt=""
        loading="eager">

      `

      :

      "";


    const summary =
      getSummary(first);


    const source =
      sourceOf(first);


    container.innerHTML = `

      <article class="lead-story">

        ${imageHTML}

        <div class="lead-shade"></div>

        <div class="lead-copy">

          <span class="signal">

            ${escapeHtml(
              first.signal ||
              "TOP SIGNAL"
            )}

          </span>


          <h3>

            ${escapeHtml(
              getTitle(first)
              ||
              "Story title unavailable"
            )}

          </h3>


          <p>

            ${escapeHtml(
              summary
              ||
              getPoints(first)[0]
              ||
              "The latest important development, explained simply."
            )}

          </p>


          <div class="lead-meta">

            ${escapeHtml(
              categoryOf(first)
            )}

            ${
              first.published_at

              ?

              " • " +
              escapeHtml(
                new Date(
                  first.published_at
                ).toLocaleDateString()
              )

              :

              ""
            }

            ${
              source
              ?

              " • Original source"

              :

              ""
            }

          </div>

        </div>

      </article>


      <div class="side-stories">

        ${
          rest.length

          ?

          rest
            .map(
              sideStory
            )
            .join("")

          :

          `

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


  function sideStory(story){

    const image =
      imageOf(story);


    return `

      <article class="side-card">

        ${
          image

          ?

          `

          <img
            src="${escapeHtml(image)}"
            alt=""
            loading="lazy">

          `

          :

          `

          <div class="story-placeholder"></div>

          `
        }


        <div>

          <span class="signal">

            ${escapeHtml(
              story.signal ||
              categoryOf(story)
            )}

          </span>


          <h3>

            ${escapeHtml(
              getTitle(story)
            )}

          </h3>


          <small>

            ${escapeHtml(
              categoryOf(story)
            )}

          </small>

        </div>

      </article>

    `;

  }


  /* =========================================================
     MORE STORIES
  ========================================================= */

  function renderMoreStories(
    stories
  ){

    const container =
      $("#stories");


    if(!container)
      return;


    const items =
      stories.slice(0,8);


    if(!items.length){

      container.innerHTML = `

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

      return;

    }


    container.innerHTML =

      items

        .map(
          story => {

            const image =
              imageOf(story);


            const source =
              sourceOf(story);


            const content = `

              ${
                image

                ?

                `

                <img
                  src="${escapeHtml(image)}"
                  alt=""
                  loading="lazy">

                `

                :

                `<div></div>`

              }


              <div>

                <h3>

                  ${escapeHtml(
                    getTitle(story)
                  )}

                </h3>


                <p>

                  ${escapeHtml(
                    getSummary(story)
                    ||
                    getPoints(story)[0]
                    ||
                    "Understand what happened and why it matters."
                  )}

                </p>

              </div>


              <span class="go">
                ›
              </span>

            `;


            if(source){

              return `

                <a
                  class="story-row"
                  href="${escapeHtml(source)}"
                  target="_blank"
                  rel="noopener noreferrer">

                  ${content}

                </a>

              `;

            }


            return `

              <div class="story-row">

                ${content}

              </div>

            `;

          }

        )

        .join("");

  }


  /* =========================================================
     LIVE WIRE
  ========================================================= */

  function renderTicker(
    stories
  ){

    const ticker =
      $("#tickerTrack");


    if(!ticker)
      return;


    const items =
      stories.slice(0,10);


    if(!items.length){

      ticker.innerHTML = `

        <span>

          <strong>● LIVE</strong>

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

              ${escapeHtml(
                getTitle(story)
              )}

            </span>

          `
        )

        .join("");


    ticker.innerHTML =
      line + line;

  }


  /* =========================================================
     COUNTS
  ========================================================= */

  function renderCounts(){

    const stories =
      state.stories
        .filter(
          hasTranslation
        );


    const location =
      state.location;


    const near =
      stories.filter(
        story =>
          locationScore(story)
          >=
          70
      ).length;


    const district =
      stories.filter(
        story =>
          locationScore(story)
          >=
          55
      ).length;


    const stateCount =
      stories.filter(
        story =>
          locationScore(story)
          >=
          30
      ).length;


    const india =
      stories.filter(
        story =>
          categoryOf(story)
          ===
          "India"
      ).length;


    const global =
      stories.filter(
        story =>
          categoryOf(story)
          ===
          "Global"
      ).length;


    $("#locationName")
      .textContent =
      locationText();


    $("#locationDetail")
      .textContent =
      locationDetail();


    $("#nearCount")
      .textContent =
      location
      ? near
      : "—";


    $("#districtCount")
      .textContent =
      location
      ? district
      : "—";


    $("#stateCount")
      .textContent =
      location
      ? stateCount
      : "—";


    $("#indiaCount")
      .textContent =
      india;


    $("#globalCount")
      .textContent =
      global;

  }


  /* =========================================================
     CONTROLS
  ========================================================= */

  function syncControls(){

    $$("[data-category]")
      .forEach(
        element => {

          element.classList.toggle(

            "active",

            element.dataset.category
            ===
            state.category

          );

        }
      );


    $$("[data-speed]")
      .forEach(
        element => {

          element.classList.toggle(

            "active",

            Number(
              element.dataset.speed
            )
            ===
            state.speed

          );

        }
      );


    $("#languageSelect")
      .value =
      state.lang;

  }


  function setCategory(
    category
  ){

    state.category =
      category;


    render();


    $("#stories")
      ?.scrollIntoView({

        behavior:"smooth",

        block:"start"

      });

  }


  /* =========================================================
     SEARCH
  ========================================================= */

  function openSearch(){

    $("#searchOverlay")
      .hidden =
      false;


    setTimeout(
      () =>
        $("#searchInput")
          .focus(),
      50
    );

  }


  function runSearch(
    query
  ){

    const q =
      query
        .trim()
        .toLowerCase();


    const results =
      $("#searchResults");


    if(!q){

      results.innerHTML =
        "";

      return;

    }


    const matches =
      state.stories

        .filter(
          story => {

            const text = [

              getTitle(story),

              getSummary(story),

              ...(getPoints(story) || []),

              categoryOf(story)

            ]

            .join(" ")
            .toLowerCase();


            return text.includes(q);

          }
        )

        .slice(0,10);


    if(!matches.length){

      results.innerHTML = `

        <div class="search-result">

          No matching story yet.

        </div>

      `;

      return;

    }


    results.innerHTML =

      matches

        .map(
          story => {

            const source =
              sourceOf(story);


            const html = `

              <strong>

                ${escapeHtml(
                  getTitle(story)
                )}

              </strong>

              <br>

              <small>

                ${escapeHtml(
                  categoryOf(story)
                )}

              </small>

            `;


            return source

              ?

              `

              <a
                class="search-result"
                href="${escapeHtml(source)}"
                target="_blank"
                rel="noopener noreferrer">

                ${html}

              </a>

              `

              :

              `

              <div class="search-result">

                ${html}

              </div>

              `;

          }
        )

        .join("");

  }


  /* =========================================================
     LOCATION MODAL
  ========================================================= */

  function openLocationModal(){

    const location =
      state.location || {};


    $("#manualState")
      .value =
      location.state || "";


    $("#manualDistrict")
      .value =
      location.district || "";


    $("#manualCity")
      .value =
      location.city || "";


    $("#manualTaluk")
      .value =
      location.taluk || "";


    $("#manualLocality")
      .value =
      location.locality || "";


    $("#locationModal")
      .hidden =
      false;

  }


  function closeLocationModal(){

    $("#locationModal")
      .hidden =
      true;

  }


  function saveManualLocation(){

    state.location = {

      country:"India",

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

      source:"manual",

      latitude:null,

      longitude:null

    };


    localStorage.setItem(

      "snippet24_location",

      JSON.stringify(
        state.location
      )

    );


    closeLocationModal();


    render();

  }


  /* =========================================================
     REVERSE GEOCODING
  ========================================================= */

  async function reverseGeocode(
    latitude,
    longitude
  ){

    const url =

      "https://api.bigdatacloud.net/data/reverse-geocode-client"

      +

      "?latitude=" +
      encodeURIComponent(latitude)

      +

      "&longitude=" +
      encodeURIComponent(longitude)

      +

      "&localityLanguage=en";


    const response =
      await fetch(url);


    if(!response.ok){

      throw new Error(
        "Reverse geocoding failed"
      );

    }


    const data =
      await response.json();


    const address =
      data.address || {};


    const administrative =
      data
        ?.localityInfo
        ?.administrative
        || [];


    const district =
      administrative.find(
        item =>
          /district/i.test(
            item.description || ""
          )
      )?.name

      ||

      address.locality

      ||

      "";


    return {

      country:
        address.countryName
        ||
        data.countryName
        ||
        "India",

      state:
        address.principalSubdivision
        ||
        "",

      district,

      city:
        address.city
        ||
        address.locality
        ||
        "",

      taluk:
        address.suburb
        ||
        "",

      locality:
        address.locality
        ||
        address.village
        ||
        "",

      latitude,

      longitude,

      source:"gps"

    };

  }


  /* =========================================================
     GPS LOCATION
  ========================================================= */

  function detectLocation(){

    if(
      !navigator.geolocation
    ){

      openLocationModal();

      return;

    }


    $("#locationName")
      .textContent =
      "Understanding your location…";


    $("#locationDetail")
      .textContent =
      "Finding your locality and weather";


    navigator.geolocation
      .getCurrentPosition(

        async position => {

          try{

            const latitude =
              position.coords.latitude;


            const longitude =
              position.coords.longitude;


            state.location =
              await reverseGeocode(
                latitude,
                longitude
              );


            localStorage.setItem(

              "snippet24_location",

              JSON.stringify(
                state.location
              )

            );


            render();


            await loadWeather();

          }

          catch(error){

            console.log(
              "Location lookup failed",
              error
            );


            openLocationModal();

          }

        },

        error => {

          console.log(
            "Location permission denied",
            error
          );


          openLocationModal();

        },

        {

          enableHighAccuracy:false,

          timeout:10000,

          maximumAge:3600000

        }

      );

  }


  /* =========================================================
     EVENTS
  ========================================================= */

  $$("[data-category]")
    .forEach(
      element => {

        element.addEventListener(
          "click",
          () => {

            setCategory(
              element.dataset.category
            );

          }
        );

      }
    );


  $("#languageSelect")
    .addEventListener(
      "change",
      event => {

        state.lang =
          event.target.value;


        localStorage.setItem(

          "snippet24_lang",

          state.lang

        );


        render();

      }
    );


  $$("[data-speed]")
    .forEach(
      element => {

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

      }
    );


  $("#searchBtn")
    .addEventListener(
      "click",
      openSearch
    );


  $("#searchClose")
    .addEventListener(
      "click",
      () => {

        $("#searchOverlay")
          .hidden =
          true;

      }
    );


  $("#searchInput")
    .addEventListener(
      "input",
      event => {

        runSearch(
          event.target.value
        );

      }
    );


  $("#menuMoreBtn")
    .addEventListener(
      "click",
      () => {

        const menu =
          $("#moreMenu");


        menu.hidden =
          !menu.hidden;

      }
    );


  $("#changeLocationBtn")
    .addEventListener(
      "click",
      openLocationModal
    );


  $("#worldArrow")
    .addEventListener(
      "click",
      openLocationModal
    );


  $("#locationModalClose")
    .addEventListener(
      "click",
      closeLocationModal
    );


  $("#locationModalBackdrop")
    .addEventListener(
      "click",
      closeLocationModal
    );


  $("#saveManualLocationBtn")
    .addEventListener(
      "click",
      saveManualLocation
    );


  $("#modalUseCurrentBtn")
    .addEventListener(
      "click",
      () => {

        closeLocationModal();

        detectLocation();

      }
    );


  /* =========================================================
     CATCH ME UP
  ========================================================= */

  $("#catchupBtn")
    .addEventListener(
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


  /* =========================================================
     VIEW ALL
  ========================================================= */

  $("#viewAllBtn")
    .addEventListener(
      "click",
      () => {

        setCategory(
          "All"
        );

      }
    );


  /* =========================================================
     PREMIUM
  ========================================================= */

  $("#premiumBtn")
    .addEventListener(
      "click",
      () => {

        window.location.href =
          "./premium.html";

      }
    );


  /* =========================================================
     START
  ========================================================= */

  loadStories();


  /*
    If a saved GPS location exists,
    load its weather immediately.
  */

  if(
    state.location?.latitude &&
    state.location?.longitude
  ){

    loadWeather();

  }


  /*
    First-time visitors:
    ask for location automatically.
  */

  if(
    !state.location
  ){

    setTimeout(
      detectLocation,
      900
    );

  }


})();