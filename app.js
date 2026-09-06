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

    weather:null

  };


  /* =========================================================
     HELPERS
  ========================================================= */

  const $ = selector =>
    document.querySelector(selector);


  const $$ = selector =>
    [...document.querySelectorAll(selector)];


  function escapeHtml(value){

    return String(value ?? "")
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

  }


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

    const value =
      story?.category ||
      story?.section ||
      "India";


    if(value === "In India")
      return "India";


    return value;

  }


  function hasTranslation(story){

    if(state.lang === "en")
      return true;


    return !!(

      story?.translations?.[state.lang]

      ||

      story?.[state.lang]

    );

  }


  /* =========================================================
     LOCATION
  ========================================================= */

  function normalize(value){

    return String(value || "")
      .trim()
      .toLowerCase();

  }


  function locationText(){

    if(!state.location)
      return "Finding your area";


    return (

      state.location.locality ||

      state.location.city ||

      state.location.town ||

      state.location.district ||

      state.location.state ||

      "Your location"

    );

  }


  function locationDetail(){

    if(!state.location)
      return "Location will be detected automatically";


    const parts = [

      state.location.district,

      state.location.state

    ].filter(Boolean);


    return parts.length

      ? parts.join(" • ")

      : "Location personalized";

  }


  function articleLocation(story){

    const location =

      story?.location ||

      story?.geo ||

      {};


    return {

      country:
        normalize(location.country),

      state:
        normalize(location.state),

      district:
        normalize(location.district),

      city:
        normalize(
          location.city ||
          location.town
        ),

      taluk:
        normalize(
          location.taluk ||
          location.block
        ),

      locality:
        normalize(
          location.locality ||
          location.village ||
          location.ward
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
        normalize(
          state.location.state
        ),

      district:
        normalize(
          state.location.district
        ),

      city:
        normalize(
          state.location.city
        ),

      taluk:
        normalize(
          state.location.taluk
        ),

      locality:
        normalize(
          state.location.locality
        )

    };


    let score = 0;


    if(
      user.locality &&
      article.locality &&
      user.locality === article.locality
    )
      score += 120;


    if(
      user.taluk &&
      article.taluk &&
      user.taluk === article.taluk
    )
      score += 95;


    if(
      user.city &&
      article.city &&
      user.city === article.city
    )
      score += 75;


    if(
      user.district &&
      article.district &&
      user.district === article.district
    )
      score += 55;


    if(
      user.state &&
      article.state &&
      user.state === article.state
    )
      score += 30;


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
          story?.importance || ""
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


    if(!Number.isFinite(timestamp))
      return 0;


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

            locationScore(b) +

            importanceScore(b) +

            freshnessScore(b)

          )

          -

          (

            locationScore(a) +

            importanceScore(a) +

            freshnessScore(a)

          )

      );

  }


  /* =========================================================
     LOAD STORIES
  ========================================================= */

  async function loadStories(){

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
      Array.isArray(data?.stories)
    ){

      state.stories =
        data.stories;

    }

    else if(
      Array.isArray(data?.articles)
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
  ========================================================= */

  async function loadWeather(){

    if(
      !state.location?.latitude ||
      !state.location?.longitude
    ){

      return;

    }


    try{

      const url =

        "https://api.open-meteo.com/v1/forecast"

        +

        "?latitude=" +
        encodeURIComponent(
          state.location.latitude
        )

        +

        "&longitude=" +
        encodeURIComponent(
          state.location.longitude
        )

        +

        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"

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


      state.weather =
        await response.json();


      renderWeather();

    }
    catch(error){

      console.log(
        "Weather unavailable"
      );

    }

  }


  function weatherDescription(code){

    const map = {

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
      71:"Snow",
      73:"Snow",
      75:"Heavy snow",
      80:"Rain showers",
      81:"Rain showers",
      82:"Heavy showers",
      95:"Thunderstorm",
      96:"Thunderstorm",
      99:"Thunderstorm"

    };


    return map[code] || "Weather";

  }


  function weatherIcon(code){

    if(code === 0)
      return "☀️";


    if(code === 1 || code === 2)
      return "⛅";


    if(code === 3)
      return "☁️";


    if(code >= 45 && code <= 48)
      return "🌫️";


    if(code >= 51 && code <= 67)
      return "🌧️";


    if(code >= 71 && code <= 77)
      return "❄️";


    if(code >= 80 && code <= 82)
      return "🌦️";


    if(code >= 95)
      return "⛈️";


    return "🌤️";

  }


  function renderWeather(){

    if(
      !state.weather?.current
    )
      return;


    const current =
      state.weather.current;


    const temp =
      Math.round(
        current.temperature_2m
      );


    const code =
      current.weather_code;


    $("#headerWeatherIcon")
      .textContent =
      weatherIcon(code);


    $("#headerWeatherTemp")
      .textContent =
      `${temp}°`;

  }


  /* =========================================================
     LOCATION DETECTION
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


    if(!response.ok)
      throw new Error(
        "Reverse geocoding failed"
      );


    const data =
      await response.json();


    const address =
      data.address || {};


    return {

      country:
        address.countryName ||
        data.countryName ||
        "India",

      state:
        address.principalSubdivision ||
        "",

      district:
        address.locality ||
        address.district ||
        "",

      city:
        address.city ||
        address.town ||
        address.locality ||
        "",

      taluk:
        address.suburb ||
        "",

      locality:
        address.locality ||
        address.village ||
        "",

      latitude,

      longitude,

      source:"gps"

    };

  }


  function detectLocation(){

    if(
      !navigator.geolocation
    ){

      showLocationUnavailable();

      return;

    }


    navigator.geolocation
      .getCurrentPosition(

        async position => {

          try{

            state.location =
              await reverseGeocode(

                position.coords.latitude,

                position.coords.longitude

              );


            localStorage.setItem(

              "snippet24_location",

              JSON.stringify(
                state.location
              )

            );


            render();


            loadWeather();

          }
          catch(error){

            console.log(
              "Location lookup failed",
              error
            );


            showLocationUnavailable();

          }

        },


        error => {

          console.log(
            "Location unavailable",
            error
          );


          /*
             IMPORTANT:
             Do NOT open a popup.
             Homepage continues normally.
          */

          showLocationUnavailable();

        },


        {

          enableHighAccuracy:false,

          timeout:10000,

          maximumAge:3600000

        }

      );

  }


  function showLocationUnavailable(){

    $("#headerWeatherTemp")
      .textContent =
      "--°";


    $("#headerWeatherIcon")
      .textContent =
      "☁️";


    $("#headerLocationName")
      .textContent =
      "Location unavailable";


    $("#aroundLocation")
      .textContent =
      "Location not shared";


    $("#aroundLocationDetail")
      .textContent =
      "Tap ✎ if you want to choose a location";

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


    syncControls();


    $("#status")
      .textContent =

      stories.length

      ?

      `${stories.length} stories`

      :

      "No published stories available yet.";

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


    const near =
      stories.filter(
        story =>
          locationScore(story) >= 70
      ).length;


    const district =
      stories.filter(
        story =>
          locationScore(story) >= 55
      ).length;


    const stateCount =
      stories.filter(
        story =>
          locationScore(story) >= 30
      ).length;


    const india =
      stories.filter(
        story =>
          categoryOf(story) === "India"
      ).length;


    const global =
      stories.filter(
        story =>
          categoryOf(story) === "Global"
      ).length;


    $("#headerLocationName")
      .textContent =
      locationText();


    $("#aroundLocation")
      .textContent =
      locationText();


    $("#aroundLocationDetail")
      .textContent =
      locationDetail();


    $("#nearCount")
      .textContent =
      state.location
      ? near
      : "—";


    $("#districtCount")
      .textContent =
      state.location
      ? district
      : "—";


    $("#stateCount")
      .textContent =
      state.location
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
     TOP STORIES
  ========================================================= */

  function renderTopStories(
    stories
  ){

    const container =
      $("#topStories");


    if(!stories.length){

      container.innerHTML = `

        <article class="lead-story">

          <div class="lead-copy">

            <span class="signal">
              SNIPPET24
            </span>

            <h3>
              Your most important stories
              will appear here.
            </h3>

            <p>
              Connect your news feed to start publishing.
            </p>

          </div>

        </article>

      `;

      return;

    }


    const first =
      stories[0];


    const rest =
      stories.slice(1,4);


    const image =
      imageOf(first);


    container.innerHTML = `

      <article class="lead-story">

        ${
          image

          ?

          `

          <img
            src="${escapeHtml(image)}"
            alt=""
            loading="eager">

          `

          :

          ""

        }


        <div class="lead-shade"></div>


        <div class="lead-copy">

          <span class="signal">
            TOP SIGNAL
          </span>


          <h3>

            ${escapeHtml(
              getTitle(first)
            )}

          </h3>


          <p>

            ${escapeHtml(
              getSummary(first)

              ||

              getPoints(first)[0]

              ||

              "Understand what happened and why it matters."
            )}

          </p>


          <div class="lead-meta">

            ${escapeHtml(
              categoryOf(first)
            )}

          </div>

        </div>

      </article>


      <div class="side-stories">

        ${
          rest
            .map(
              story => {

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

                      `<div class="story-placeholder"></div>`

                    }


                    <div>

                      <span class="signal">

                        ${escapeHtml(
                          categoryOf(story)
                        )}

                      </span>


                      <h3>

                        ${escapeHtml(
                          getTitle(story)
                        )}

                      </h3>


                      <small>
                        Snippet24
                      </small>

                    </div>

                  </article>

                `;

              }
            )
            .join("")

        }

      </div>

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
              Connect your news feed to start publishing.
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


            const html = `

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

                  ${html}

                </a>

              `;

            }


            return `

              <div class="story-row">

                ${html}

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


    if(!stories.length){

      ticker.innerHTML = `

        <span>

          <strong>● LIVE</strong>

          Waiting for the latest Snippet24 signal…

        </span>

      `;

      return;

    }


    const line =

      stories
        .slice(0,10)
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
          No matching story found.
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

      locality:
        $("#manualLocality")
          .value
          .trim(),

      latitude:null,

      longitude:null,

      source:"manual"

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
     CATEGORY
  ========================================================= */

  function setCategory(
    category
  ){

    state.category =
      category;


    render();

  }


  /* =========================================================
     CONTROLS
  ========================================================= */

  function syncControls(){

    $$("[data-category]")
      .forEach(
        button => {

          button.classList.toggle(

            "active",

            button.dataset.category
            ===
            state.category

          );

        }
      );


    $$("[data-speed]")
      .forEach(
        button => {

          button.classList.toggle(

            "active",

            Number(
              button.dataset.speed
            )
            ===
            state.speed

          );

        }
      );

  }


  $$("[data-category]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            setCategory(
              button.dataset.category
            );

          }
        );

      }
    );


  $$("[data-speed]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            state.speed =
              Number(
                button.dataset.speed
              );


            syncControls();

          }
        );

      }
    );


  /* =========================================================
     EVENTS
  ========================================================= */

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


  $("#moreBtn")
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


  $("#locationModalClose")
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
          .scrollIntoView({
            behavior:"smooth"
          });

      }
    );


  $("#viewAllBtn")
    .addEventListener(
      "click",
      () => {

        setCategory(
          "All"
        );

      }
    );


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
    Existing saved GPS location:
    load weather silently.
  */

  if(
    state.location?.latitude &&
    state.location?.longitude
  ){

    loadWeather();

  }


  /*
    New visitor:
    detect location silently.
    NEVER open a location popup automatically.
  */

  if(!state.location){

    setTimeout(
      detectLocation,
      700
    );

  }


})();