(() => {

  "use strict";


  /* =====================================================
     SNIPPET24 FRONTEND
     GitHub Pages compatible
     No browser GPS permission
  ===================================================== */


  const $ = selector =>
    document.querySelector(selector);

  const $$ = selector =>
    Array.from(document.querySelectorAll(selector));


  const STORAGE_KEY =
    "snippet24_location";


  const state = {

    location:null,

    stories:[],

    activeCategory:"all"

  };


  /* =====================================================
     STORAGE
  ===================================================== */

  function getSavedLocation(){

    try{

      const raw =
        localStorage.getItem(STORAGE_KEY);

      if(!raw){
        return null;
      }

      const parsed =
        JSON.parse(raw);

      if(
        !parsed ||
        typeof parsed !== "object"
      ){
        return null;
      }

      return parsed;

    }catch{

      return null;

    }

  }


  function saveLocation(location){

    try{

      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(location)
      );

    }catch{

      // Storage unavailable.

    }

  }


  /* =====================================================
     TEXT SAFETY
  ===================================================== */

  function esc(value){

    return String(value ?? "")
      .replace(/&/g,"&amp;")
      .replace(/</g,"&lt;")
      .replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;")
      .replace(/'/g,"&#039;");

  }


  /* =====================================================
     URL SAFETY
  ===================================================== */

  function safeExternalUrl(value){

    if(!value){
      return null;
    }

    try{

      const url =
        new URL(
          String(value),
          window.location.href
        );

      if(
        url.protocol !== "https:" &&
        url.protocol !== "http:"
      ){
        return null;
      }

      return url.href;

    }catch{

      return null;

    }

  }


  /* =====================================================
     FETCH WITH TIMEOUT
  ===================================================== */

  async function fetchWithTimeout(
    url,
    timeout = 8000
  ){

    const controller =
      new AbortController();

    const timer =
      setTimeout(
        () => controller.abort(),
        timeout
      );

    try{

      const response =
        await fetch(
          url,
          {
            cache:"no-store",
            signal:controller.signal
          }
        );

      return response;

    }finally{

      clearTimeout(timer);

    }

  }


  /* =====================================================
     STORY FIELD NORMALIZATION
  ===================================================== */

  function storyTitle(story){

    return (
      story.headline ||
      story.title ||
      story.name ||
      story.story_title ||
      "Untitled story"
    );

  }


  function storySummary(story){

    return (
      story.summary ||
      story.description ||
      story.snippet ||
      story.excerpt ||
      story.short_summary ||
      story.content ||
      ""
    );

  }


  function storySource(story){

    return (
      story.source_name ||
      story.source ||
      story.publisher ||
      story.source_title ||
      "Snippet24"
    );

  }


  function storyUrl(story){

    return safeExternalUrl(
      story.url ||
      story.link ||
      story.source_url ||
      story.article_url ||
      story.original_url
    );

  }


  function storyLocationText(story){

    return [

      story.location,
      story.city,
      story.town,
      story.village,
      story.locality,
      story.area,
      story.district,
      story.state,
      story.region,
      story.place

    ]
      .filter(Boolean)
      .join(" ");

  }


  /* =====================================================
     CATEGORY NORMALIZATION
  ===================================================== */

  function normalizeCategory(story){

    const raw = [

      story.category,
      story.section,
      story.topic,
      story.section_name

    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();


    if(
      raw.includes("business") ||
      raw.includes("econom") ||
      raw.includes("finance") ||
      raw.includes("money")
    ){

      return "business";

    }


    if(
      raw.includes("tech") ||
      raw.includes("ai") ||
      raw.includes("science")
    ){

      return "tech";

    }


    if(raw.includes("sport")){

      return "sports";

    }


    if(
      raw.includes("people") ||
      raw.includes("culture") ||
      raw.includes("society")
    ){

      return "people";

    }


    if(
      raw.includes("global") ||
      raw.includes("world") ||
      raw.includes("international")
    ){

      return "global";

    }


    if(
      raw.includes("india") ||
      raw.includes("state") ||
      raw.includes("local")
    ){

      return "india";

    }


    return "india";

  }


  /* =====================================================
     LOAD ARTICLES.JSON
  ===================================================== */

  async function loadArticlesJson(){

    const response =
      await fetchWithTimeout(
        "./articles.json?v=20260907",
        10000
      );

    if(!response.ok){

      throw new Error(
        `articles.json HTTP ${response.status}`
      );

    }

    return response.json();

  }


  /* =====================================================
     LOAD API
  ===================================================== */

  async function loadApiStories(){

    const response =
      await fetchWithTimeout(
        "./api/stories",
        8000
      );

    if(!response.ok){

      throw new Error(
        `API HTTP ${response.status}`
      );

    }

    return response.json();

  }


  /* =====================================================
     NORMALIZE ARTICLE RESPONSE
  ===================================================== */

  function extractStories(data){

    if(Array.isArray(data)){

      return data;

    }


    if(
      data &&
      Array.isArray(data.articles)
    ){

      return data.articles;

    }


    if(
      data &&
      Array.isArray(data.stories)
    ){

      return data.stories;

    }


    if(
      data &&
      data.data &&
      Array.isArray(data.data)
    ){

      return data.data;

    }


    return [];

  }


  /* =====================================================
     MAIN STORY LOADER
  ===================================================== */

  async function loadStories(){

    let stories = [];


    /*
      GitHub Pages cannot execute server.js.

      Therefore articles.json is deliberately loaded FIRST.
    */

    try{

      const data =
        await loadArticlesJson();

      stories =
        extractStories(data);

    }catch(error){

      console.warn(
        "articles.json unavailable:",
        error
      );


      /*
        Optional API fallback for environments
        where /api/stories exists.
      */

      try{

        const data =
          await loadApiStories();

        stories =
          extractStories(data);

      }catch(apiError){

        console.warn(
          "API unavailable:",
          apiError
        );

      }

    }


    state.stories =
      stories.filter(
        story =>
          story &&
          typeof story === "object"
      );


    renderStories();

    renderTicker();

    renderCounts();

  }


  /* =====================================================
     TOP STORIES
  ===================================================== */

  function createStoryCard(story){

    const title =
      esc(storyTitle(story));

    const summary =
      esc(storySummary(story));

    const source =
      esc(storySource(story));

    const category =
      esc(
        story.category ||
        story.section ||
        normalizeCategory(story)
      );


    const url =
      storyUrl(story);


    return `

      <article class="story-card">

        <span class="story-category">
          ${category}
        </span>

        <h3>
          ${title}
        </h3>

        <p>
          ${summary}
        </p>

        <div class="story-source">
          Source: ${source}
        </div>

        ${
          url
            ?
            `
            <a
              href="${esc(url)}"
              target="_blank"
              rel="noopener noreferrer">
              READ SOURCE →
            </a>
            `
            :
            ""
        }

      </article>

    `;

  }


  function renderTopStories(){

    const container =
      $("#topStoriesGrid");

    if(!container){
      return;
    }


    const stories =
      state.stories.slice(0,6);


    if(!stories.length){

      container.innerHTML = `

        <article class="waiting-card">

          <span>●</span>

          <h3>
            NEWS FEED UNAVAILABLE
          </h3>

          <p>
            Snippet24 is waiting for the latest stories.
          </p>

        </article>

      `;

      return;

    }


    container.innerHTML =
      stories
        .map(createStoryCard)
        .join("");

  }


  /* =====================================================
     MORE NEWS
  ===================================================== */

  function renderMoreNews(){

    const container =
      $("#moreNewsGrid");

    if(!container){
      return;
    }


    let stories =
      state.stories;


    if(
      state.activeCategory !== "all"
    ){

      stories =
        stories.filter(
          story =>
            normalizeCategory(story) ===
            state.activeCategory
        );

    }


    stories =
      stories.slice(0,18);


    if(!stories.length){

      container.innerHTML = `

        <p class="empty-state">
          No stories found for this section yet.
        </p>

      `;

      return;

    }


    container.innerHTML =
      stories
        .map(story => {

          const title =
            esc(storyTitle(story));

          const summary =
            esc(storySummary(story));

          const category =
            esc(
              story.category ||
              story.section ||
              normalizeCategory(story)
            );

          const url =
            storyUrl(story);


          return `

            <article class="more-story">

              <span class="story-category">
                ${category}
              </span>

              <h3>
                ${title}
              </h3>

              <p>
                ${summary}
              </p>

              ${
                url
                  ?
                  `
                  <a
                    href="${esc(url)}"
                    target="_blank"
                    rel="noopener noreferrer">
                    READ →
                  </a>
                  `
                  :
                  ""
              }

            </article>

          `;

        })
        .join("");

  }


  function renderStories(){

    renderTopStories();

    renderMoreNews();

  }


  /* =====================================================
     LIVE WIRE
  ===================================================== */

  function renderTicker(){

    const ticker =
      $("#liveTicker");

    if(!ticker){
      return;
    }


    const stories =
      state.stories.slice(0,10);


    if(!stories.length){

      ticker.innerHTML =
        `
        <span>
          Snippet24 Live Wire — waiting for the latest updates…
        </span>
        `;

      return;

    }


    ticker.innerHTML =
      stories
        .map(
          story =>
            `
            <span>
              ${esc(storyTitle(story))}
            </span>
            `
        )
        .join("");

  }


  /* =====================================================
     LOCATION
  ===================================================== */

  async function detectLocation(){

    const place =
      $("#weatherPlace");


    if(place){

      place.textContent =
        "Detecting area…";

    }


    try{

      /*
        IMPORTANT:
        This is IP-based.
        navigator.geolocation is NOT used.
      */

      const response =
        await fetchWithTimeout(
          "https://ipapi.co/json/",
          8000
        );


      if(!response.ok){

        throw new Error(
          "IP location unavailable"
        );

      }


      const data =
        await response.json();


      const latitude =
        Number(data.latitude);

      const longitude =
        Number(data.longitude);


      if(
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude)
      ){

        throw new Error(
          "Invalid coordinates"
        );

      }


      state.location = {

        city:
          data.city ||
          "",

        district:
          data.district ||
          "",

        state:
          data.region ||
          "",

        country:
          data.country_name ||
          "",

        latitude,
        longitude,

        source:"ip"

      };


      saveLocation(
        state.location
      );


      await enrichLocation();


      updateLocationUI();

      await updateWeather();

      renderCounts();


    }catch(error){

      console.warn(
        "Location detection failed:",
        error
      );


      if(place){

        place.textContent =
          "Location unavailable";

      }

    }

  }


  /* =====================================================
     REVERSE GEOCODE
  ===================================================== */

  async function enrichLocation(){

    if(!state.location){
      return;
    }


    const lat =
      Number(
        state.location.latitude
      );

    const lon =
      Number(
        state.location.longitude
      );


    if(
      !Number.isFinite(lat) ||
      !Number.isFinite(lon)
    ){

      return;

    }


    try{

      const url =
        "https://api.bigdatacloud.net/data/reverse-geocode-client" +
        `?latitude=${encodeURIComponent(lat)}` +
        `&longitude=${encodeURIComponent(lon)}` +
        "&localityLanguage=en";


      const response =
        await fetchWithTimeout(
          url,
          8000
        );


      if(!response.ok){
        return;
      }


      const data =
        await response.json();


      const city =
        data.city ||
        data.locality ||
        data.localityInfo?.administrativeArea?.[3]?.name ||
        "";


      const district =
        data.localityInfo?.administrativeArea?.find(
          item =>
            String(
              item.name || ""
            )
              .toLowerCase()
              .includes("district")
        )?.name ||
        data.principalSubdivision ||
        "";


      const stateName =
        data.principalSubdivision ||
        "";


      if(city){
        state.location.city = city;
      }


      if(district){
        state.location.district =
          district;
      }


      if(stateName){
        state.location.state =
          stateName;
      }


      saveLocation(
        state.location
      );


    }catch(error){

      console.warn(
        "Reverse geocoding failed:",
        error
      );

    }

  }


  /* =====================================================
     LOCATION UI
  ===================================================== */

  function updateLocationUI(){

    const place =
      $("#weatherPlace");


    if(!place){
      return;
    }


    if(!state.location){

      place.textContent =
        "Detecting area…";

      return;

    }


    const name =
      state.location.city ||
      state.location.district ||
      state.location.state ||
      "Your area";


    place.textContent =
      name;

  }


  /* =====================================================
     WEATHER
  ===================================================== */

  function weatherDescription(code){

    const map = {

      0:["☀","Clear"],
      1:["🌤","Mainly clear"],
      2:["⛅","Partly cloudy"],
      3:["☁","Cloudy"],
      45:["🌫","Fog"],
      48:["🌫","Fog"],
      51:["🌦","Drizzle"],
      53:["🌦","Drizzle"],
      55:["🌧","Drizzle"],
      61:["🌧","Rain"],
      63:["🌧","Rain"],
      65:["🌧","Heavy rain"],
      71:["🌨","Snow"],
      73:["🌨","Snow"],
      75:["❄","Snow"],
      80:["🌦","Showers"],
      81:["🌦","Showers"],
      82:["⛈","Heavy showers"],
      95:["⛈","Thunderstorm"],
      96:["⛈","Thunderstorm"],
      99:["⛈","Thunderstorm"]

    };


    return (
      map[code] ||
      ["☁","Weather"]
    );

  }


  async function updateWeather(){

    if(!state.location){
      return;
    }


    const lat =
      Number(
        state.location.latitude
      );

    const lon =
      Number(
        state.location.longitude
      );


    if(
      !Number.isFinite(lat) ||
      !Number.isFinite(lon)
    ){

      return;

    }


    try{

      const url =
        "https://api.open-meteo.com/v1/forecast" +
        `?latitude=${encodeURIComponent(lat)}` +
        `&longitude=${encodeURIComponent(lon)}` +
        "&current=temperature_2m,weather_code" +
        "&timezone=auto" +
        "&forecast_days=1";


      const response =
        await fetchWithTimeout(
          url,
          8000
        );


      if(!response.ok){
        throw new Error(
          "Weather unavailable"
        );
      }


      const data =
        await response.json();


      const temperature =
        Number(
          data.current?.temperature_2m
        );


      const code =
        data.current?.weather_code;


      if(
        Number.isFinite(
          temperature
        )
      ){

        $("#weatherTemp").textContent =
          `${Math.round(temperature)}°`;

      }


      const [icon] =
        weatherDescription(code);


      $("#weatherIcon").textContent =
        icon;


    }catch(error){

      console.warn(
        "Weather failed:",
        error
      );

    }

  }


  /* =====================================================
     LOCAL STORY MATCHING
  ===================================================== */

  function containsLocation(
    story,
    locationValue
  ){

    if(!locationValue){
      return false;
    }


    const target =
      String(
        locationValue
      )
        .trim()
        .toLowerCase();


    if(target.length < 3){
      return false;
    }


    const text =
      storyLocationText(story)
        .toLowerCase();


    const title =
      storyTitle(story)
        .toLowerCase();


    const summary =
      storySummary(story)
        .toLowerCase();


    return (
      text.includes(target) ||
      title.includes(target) ||
      summary.includes(target)
    );

  }


  function getNearStories(){

    if(!state.location){
      return [];
    }


    return state.stories.filter(
      story => {

        return (
          containsLocation(
            story,
            state.location.city
          ) ||
          containsLocation(
            story,
            state.location.locality
          ) ||
          containsLocation(
            story,
            state.location.taluk
          )
        );

      }
    );

  }


  function getDistrictStories(){

    if(!state.location){
      return [];
    }


    return state.stories.filter(
      story =>
        containsLocation(
          story,
          state.location.district
        )
    );

  }


  function getStateStories(){

    if(!state.location){
      return [];
    }


    return state.stories.filter(
      story =>
        containsLocation(
          story,
          state.location.state
        )
    );

  }


  /* =====================================================
     COUNTS
  ===================================================== */

  function renderCounts(){

    const near =
      $("#nearCount");

    const district =
      $("#districtCount");

    const stateCount =
      $("#stateCount");


    if(!state.location){

      if(near) near.textContent = "—";

      if(district) district.textContent = "—";

      if(stateCount) stateCount.textContent = "—";

      return;

    }


    const nearStories =
      getNearStories();

    const districtStories =
      getDistrictStories();

    const stateStories =
      getStateStories();


    if(near){

      near.textContent =
        nearStories.length;

    }


    if(district){

      district.textContent =
        districtStories.length;

    }


    if(stateCount){

      stateCount.textContent =
        stateStories.length;

    }

  }


  /* =====================================================
     SHOW LOCAL STORIES
  ===================================================== */

  function showLocalStories(type){

    if(!state.location){

      openLocationModal();

      return;

    }


    let stories = [];


    if(type === "near"){

      stories =
        getNearStories();

    }


    if(type === "district"){

      stories =
        getDistrictStories();

    }


    if(type === "state"){

      stories =
        getStateStories();

    }


    const target =
      $("#moreNewsGrid");


    if(!target){
      return;
    }


    if(!stories.length){

      target.innerHTML = `

        <p class="empty-state">
          No local stories found yet.
        </p>

      `;

    }else{

      target.innerHTML =
        stories
          .slice(0,18)
          .map(story => {

            const url =
              storyUrl(story);


            return `

              <article class="more-story">

                <span class="story-category">
                  LOCAL
                </span>

                <h3>
                  ${esc(
                    storyTitle(story)
                  )}
                </h3>

                <p>
                  ${esc(
                    storySummary(story)
                  )}
                </p>

                ${
                  url
                    ?
                    `
                    <a
                      href="${esc(url)}"
                      target="_blank"
                      rel="noopener noreferrer">
                      READ →
                    </a>
                    `
                    :
                    ""
                }

              </article>

            `;

          })
          .join("");

    }


    $("#more")?.scrollIntoView({
      behavior:"smooth"
    });

  }


  /* =====================================================
     LOCATION MODAL
  ===================================================== */

  function openLocationModal(){

    const modal =
      $("#locationOverlay");


    if(!modal){
      return;
    }


    const location =
      state.location;


    if(location){

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

    }


    modal.hidden = false;

  }


  function closeLocationModal(){

    const modal =
      $("#locationOverlay");


    if(modal){

      modal.hidden = true;

    }

  }


  function saveManualLocation(){

    const location = {

      state:
        $("#manualState").value.trim(),

      district:
        $("#manualDistrict").value.trim(),

      city:
        $("#manualCity").value.trim(),

      taluk:
        $("#manualTaluk").value.trim(),

      locality:
        $("#manualLocality").value.trim(),

      source:"manual"

    };


    if(
      !location.state &&
      !location.district &&
      !location.city
    ){

      return;

    }


    state.location =
      location;


    saveLocation(
      location
    );


    updateLocationUI();

    renderCounts();

    closeLocationModal();

  }


  /* =====================================================
     SEARCH
  ===================================================== */

  function openSearch(){

    const overlay =
      $("#searchOverlay");


    if(!overlay){
      return;
    }


    overlay.hidden = false;


    setTimeout(
      () =>
        $("#searchInput")?.focus(),
      50
    );

  }


  function closeSearch(){

    const overlay =
      $("#searchOverlay");


    if(overlay){

      overlay.hidden = true;

    }

  }


  function performSearch(query){

    const results =
      $("#searchResults");


    if(!results){
      return;
    }


    const q =
      query
        .trim()
        .toLowerCase();


    if(!q){

      results.innerHTML = "";

      return;

    }


    const matches =
      state.stories
        .filter(story => {

          const text = [

            storyTitle(story),
            storySummary(story),
            story.category,
            story.section,
            storyLocationText(story),
            storySource(story)

          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();


          return text.includes(q);

        })
        .slice(0,10);


    if(!matches.length){

      results.innerHTML = `

        <p class="empty-state">
          No stories found for
          “${esc(query)}”.
        </p>

      `;

      return;

    }


    results.innerHTML =
      matches
        .map(story => {

          const url =
            storyUrl(story);


          return `

            <div class="search-result">

              <small>
                ${esc(
                  storySource(story)
                )}
              </small>

              <h3>
                ${esc(
                  storyTitle(story)
                )}
              </h3>

              <p>
                ${esc(
                  storySummary(story)
                )}
              </p>

              ${
                url
                  ?
                  `
                  <a
                    href="${esc(url)}"
                    target="_blank"
                    rel="noopener noreferrer">
                    READ SOURCE →
                  </a>
                  `
                  :
                  ""
              }

            </div>

          `;

        })
        .join("");

  }


  /* =====================================================
     CATCH ME UP
  ===================================================== */

  function catchMeUp(){

    $("#topStories")?.scrollIntoView({
      behavior:"smooth"
    });

  }


  /* =====================================================
     MENU
  ===================================================== */

  function openMenu(){

    $("#mainNav")?.scrollIntoView({
      behavior:"smooth"
    });

  }


  /* =====================================================
     EVENTS
  ===================================================== */

  function bindEvents(){


    /* Search */

    $("#searchBtn")?.addEventListener(
      "click",
      openSearch
    );


    $("#closeSearch")?.addEventListener(
      "click",
      closeSearch
    );


    $("#searchOverlay")?.addEventListener(
      "click",
      event => {

        if(
          event.target.id ===
          "searchOverlay"
        ){

          closeSearch();

        }

      }
    );


    $("#searchForm")?.addEventListener(
      "submit",
      event => {

        event.preventDefault();

        performSearch(
          $("#searchInput").value
        );

      }
    );


    $("#searchInput")?.addEventListener(
      "input",
      event => {

        performSearch(
          event.target.value
        );

      }
    );


    /* Location */

    $("#changeLocation")?.addEventListener(
      "click",
      openLocationModal
    );


    $("#closeLocation")?.addEventListener(
      "click",
      closeLocationModal
    );


    $("#locationOverlay")?.addEventListener(
      "click",
      event => {

        if(
          event.target.id ===
          "locationOverlay"
        ){

          closeLocationModal();

        }

      }
    );


    $("#saveLocation")?.addEventListener(
      "click",
      saveManualLocation
    );


    $("#detectAutomatic")?.addEventListener(
      "click",
      async () => {

        closeLocationModal();

        await detectLocation();

      }
    );


    /* Catch up */

    $("#catchUpBtn")?.addEventListener(
      "click",
      catchMeUp
    );


    /* Around You */

    $("#nearCard")?.addEventListener(
      "click",
      () =>
        showLocalStories("near")
    );


    $("#districtCard")?.addEventListener(
      "click",
      () =>
        showLocalStories("district")
    );


    $("#stateCard")?.addEventListener(
      "click",
      () =>
        showLocalStories("state")
    );


    $("#worldArrow")?.addEventListener(
      "click",
      () =>
        showLocalStories("near")
    );


    /* Category tabs */

    $$(".category-tab").forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            $$(".category-tab")
              .forEach(
                item =>
                  item.classList.remove(
                    "active"
                  )
              );


            button.classList.add(
              "active"
            );


            state.activeCategory =
              button.dataset.category ||
              "all";


            renderMoreNews();

          }
        );

      }
    );


    /* Menu */

    $("#menuBtn")?.addEventListener(
      "click",
      openMenu
    );


    /* Escape */

    document.addEventListener(
      "keydown",
      event => {

        if(
          event.key === "Escape"
        ){

          closeSearch();

          closeLocationModal();

        }

      }
    );

  }


  /* =====================================================
     INITIALIZE
  ===================================================== */

  async function init(){

    bindEvents();


    /*
      First use saved manual/IP location.
      Otherwise silently detect approximate IP location.
    */

    state.location =
      getSavedLocation();


    if(state.location){

      updateLocationUI();

      updateWeather();

      renderCounts();

    }else{

      detectLocation();

    }


    /*
      Load the actual Snippet24 articles.
    */

    await loadStories();

  }


  init();

})();