(() => {

  "use strict";


  /* =========================================================
     STATE
  ========================================================= */

  const state = {

    stories: [],

    category: "All",

    speed: 10,

    page: 1,

    pageSize: 12,

    loading: false,

    location: safeRead("snippet24_location"),

    lang: "en"

  };


  /* =========================================================
     HELPERS
  ========================================================= */

  const $ = selector =>
    document.querySelector(selector);


  const $$ = selector =>
    [...document.querySelectorAll(selector)];


  function safeRead(key){

    try{

      return JSON.parse(
        localStorage.getItem(key) || "null"
      );

    }catch(error){

      try{
        localStorage.removeItem(key);
      }catch(_){}

      return null;

    }

  }


  function safeWrite(key,value){

    try{

      localStorage.setItem(
        key,
        JSON.stringify(value)
      );

    }catch(_){}

  }


  function esc(value){

    return String(value ?? "")
      .replace(/[&<>"']/g, character => ({
        "&":"&amp;",
        "<":"&lt;",
        ">":"&gt;",
        '"':"&quot;",
        "'":"&#39;"
      }[character]));

  }


  function safeUrl(value){

    try{

      const url = new URL(
        String(value || ""),
        location.href
      );

      if(
        url.protocol !== "https:" &&
        url.protocol !== "http:"
      ){

        return "";

      }

      return url.href;

    }catch(_){

      return "";

    }

  }


  /* =========================================================
     ARTICLE FIELDS
  ========================================================= */

  function titleOf(article){

    return (

      article?.translations?.[state.lang]?.title ||

      article?.[state.lang]?.title ||

      article?.headline ||

      article?.title ||

      ""

    );

  }


  function summaryOf(article){

    return (

      article?.translations?.[state.lang]?.summary ||

      article?.[state.lang]?.summary ||

      article?.summary ||

      ""

    );

  }


  function pointsOf(article){

    const points =

      article?.translations?.[state.lang]?.key_points ||

      article?.[state.lang]?.key_points ||

      article?.key_points ||

      article?.snippet_lines ||

      [];

    return Array.isArray(points)
      ? points
      : [String(points || "")];

  }


  function imageOf(article){

    return (

      article?.ai_image_url ||

      article?.image_url ||

      article?.image ||

      article?.local_image ||

      ""

    );

  }


  function sourceOf(article){

    return (

      article?.source_url ||

      article?.original_source_url ||

      article?.original_url ||

      article?.url ||

      ""

    );

  }


  function categoryOf(article){

    const raw = String(
      article?.category ||
      article?.section ||
      "India"
    ).trim();

    if(raw === "In India"){

      return "India";

    }

    return raw;

  }


  function publishedTime(article){

    const time = Date.parse(

      article?.published_at ||

      article?.updated_at ||

      ""

    );

    return Number.isFinite(time)
      ? time
      : 0;

  }


  function freshnessScore(article){

    const published = publishedTime(article);

    if(!published){

      return 0;

    }

    return Math.max(
      0,
      40 -
      (
        (Date.now() - published) /
        3600000
      )
    );

  }


  function importanceScore(article){

    return (

      {
        CRITICAL:80,
        HIGH:50,
        MEDIUM:20,
        LOW:5
      }[
        String(
          article?.importance || ""
        ).toUpperCase()
      ] || 10

    );

  }


  /* =========================================================
     LOCATION
  ========================================================= */

  function storyLocation(article){

    const location =
      article?.location ||
      article?.geo ||
      {};

    return {

      country:
        String(
          location.country || ""
        ).toLowerCase(),

      state:
        String(
          location.state || ""
        ).toLowerCase(),

      district:
        String(
          location.district || ""
        ).toLowerCase(),

      city:
        String(
          location.city ||
          location.town ||
          ""
        ).toLowerCase(),

      taluk:
        String(
          location.taluk ||
          location.block ||
          ""
        ).toLowerCase(),

      locality:
        String(
          location.locality ||
          location.village ||
          location.ward ||
          ""
        ).toLowerCase()

    };

  }


  function locationScore(article){

    if(!state.location){

      return 0;

    }

    const story = storyLocation(article);

    const current = state.location;

    const value = key =>
      String(
        current?.[key] || ""
      ).toLowerCase();

    let score = 0;


    if(
      value("locality") &&
      story.locality === value("locality")
    ){

      score += 120;

    }


    if(
      value("taluk") &&
      story.taluk === value("taluk")
    ){

      score += 95;

    }


    if(
      value("city") &&
      story.city === value("city")
    ){

      score += 75;

    }


    if(
      value("district") &&
      story.district === value("district")
    ){

      score += 55;

    }


    if(
      value("state") &&
      story.state === value("state")
    ){

      score += 30;

    }


    return score;

  }


  /* =========================================================
     FILTER / SORT
  ========================================================= */

  function allFiltered(){

    return state.stories

      .filter(article => {

        return (
          state.category === "All" ||
          categoryOf(article) === state.category
        );

      })

      .sort((a,b) => {

        const scoreA =
          locationScore(a) +
          importanceScore(a) +
          freshnessScore(a);

        const scoreB =
          locationScore(b) +
          importanceScore(b) +
          freshnessScore(b);

        return (

          scoreB - scoreA ||

          publishedTime(b) -
          publishedTime(a)

        );

      });

  }


  /* =========================================================
     STATUS
  ========================================================= */

  function setStatus(text){

    const element =
      $("#status");

    if(element){

      element.textContent = text;

    }

  }


  /* =========================================================
     LOCATION DISPLAY
  ========================================================= */

  function locationText(){

    if(!state.location){

      return "Finding your area";

    }

    return (

      state.location.city ||

      state.location.locality ||

      state.location.district ||

      state.location.state ||

      "Your area"

    );

  }


  function locationDetail(){

    if(!state.location){

      return "Personalized from your area";

    }

    return (

      [
        state.location.district,
        state.location.state
      ]

      .filter(Boolean)

      .join(" • ") ||

      "Location personalized"

    );

  }


  /* =========================================================
     MAIN RENDER
  ========================================================= */

  function render(){

    const list =
      allFiltered();


    renderHeroStories(list);

    renderMoreStories(list);

    renderTicker(list);

    renderCounts();

    syncControls();


    if(list.length){

      setStatus(
        `${list.length} stories • showing ${Math.min(
          list.length,
          state.page * state.pageSize
        )}`
      );

    }else{

      setStatus(
        "No published stories available yet."
      );

    }

  }


  /* =========================================================
     TOP STORIES
  ========================================================= */

  function renderHeroStories(list){

    const box =
      $("#topStories");

    if(!box){

      return;

    }


    const first =
      list[0];

    const rest =
      list.slice(1,4);


    if(!first){

      box.innerHTML = `

        <div class="lead-story">

          <div class="lead-copy">

            <span class="signal">
              WAITING FOR SIGNAL
            </span>

            <h3>
              Your latest important stories
              will appear here.
            </h3>

            <p>
              The news feed is ready.
              Add articles.json to the same
              GitHub Pages root as index.html.
            </p>

          </div>

        </div>

      `;

      return;

    }


    const image =
      safeUrl(imageOf(first));

    const title =
      esc(
        titleOf(first) ||
        "Story title unavailable"
      );


    const summary =
      esc(
        summaryOf(first) ||
        pointsOf(first)
          .filter(Boolean)
          .slice(0,3)
          .join(" • ") ||
        "The latest important development, explained simply."
      );


    const meta =
      `${esc(categoryOf(first))}${
        first.published_at
          ? " • " +
            esc(
              new Date(
                first.published_at
              ).toLocaleDateString()
            )
          : ""
      }`;


    box.innerHTML = `

      <article class="lead-story">

        ${
          image

          ?

          `
          <img
            src="${esc(image)}"
            alt=""
            loading="eager"
            decoding="async"
            onerror="this.remove()">
          `

          :

          ""

        }

        <div class="shade"></div>

        <div class="lead-copy">

          <span class="signal">
            ${esc(
              first.signal ||
              "TOP SIGNAL"
            )}
          </span>

          <h3>
            ${title}
          </h3>

          <p>
            ${summary}
          </p>

          <div class="lead-meta">

            ${meta}

            ${
              sourceOf(first)
                ? " • Original source"
                : ""
            }

          </div>

        </div>

      </article>


      <div class="side-stories">

        ${rest.map(sideCard).join("")}

      </div>

    `;

  }


  function sideCard(article){

    const image =
      safeUrl(
        imageOf(article)
      );


    return `

      <article class="side-card">

        ${
          image

          ?

          `
          <img
            src="${esc(image)}"
            alt=""
            loading="lazy"
            decoding="async"
            onerror="this.style.display='none'">
          `

          :

          `
          <div class="story-image"></div>
          `

        }


        <div>

          <span class="signal">

            ${esc(
              article.signal ||
              categoryOf(article)
            )}

          </span>


          <h3>

            ${esc(
              titleOf(article) ||
              "Story title unavailable"
            )}

          </h3>


          <small>

            ${esc(
              categoryOf(article)
            )}

          </small>

        </div>

      </article>

    `;

  }


  /* =========================================================
     MORE STORIES
  ========================================================= */

  function renderMoreStories(list){

    const box =
      $("#stories");

    if(!box){

      return;

    }


    const visible =
      list.slice(
        0,
        state.page *
        state.pageSize
      );


    if(!visible.length){

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


    box.innerHTML = visible.map(article => {

      const image =
        safeUrl(
          imageOf(article)
        );

      const source =
        safeUrl(
          sourceOf(article)
        );


      const summary =
        summaryOf(article) ||
        pointsOf(article)[0] ||
        "Understand what happened and why it matters.";


      const content = `

        ${
          image

          ?

          `
          <img
            src="${esc(image)}"
            alt=""
            loading="lazy"
            decoding="async"
            onerror="this.style.display='none'">
          `

          :

          `<div></div>`

        }


        <div>

          <h3>
            ${esc(
              titleOf(article) ||
              "Story title unavailable"
            )}
          </h3>

          <p>
            ${esc(summary)}
          </p>

          <small class="story-attribution">

            ${esc(
              article.publisher ||
              article.source_label ||
              "Original source"
            )}

          </small>

        </div>


        <span class="go">
          ›
        </span>

      `;


      if(source){

        return `

          <a
            class="story-row"
            href="${esc(source)}"
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

    }).join("");


    if(list.length > visible.length){

      box.insertAdjacentHTML(

        "beforeend",

        `

        <button
          class="load-more"
          id="loadMoreBtn">

          LOAD MORE STORIES

          <span>
            ↓
          </span>

        </button>

        `

      );


      $("#loadMoreBtn")
        ?.addEventListener(
          "click",
          () => {

            state.page += 1;

            render();

          }
        );

    }

  }


  /* =========================================================
     LIVE WIRE
  ========================================================= */

  function renderTicker(list){

    const element =
      $("#tickerTrack");

    if(!element){

      return;

    }


    const items =
      list.slice(0,12);


    if(!items.length){

      element.innerHTML = `

        <span>
          LIVE • Waiting for the latest
          Snippet24 signal…
        </span>

      `;

      return;

    }


    const line =
      items.map(article => `

        <span>

          <strong>
            ●
          </strong>

          ${esc(
            titleOf(article)
          )}

        </span>

      `).join("");


    element.innerHTML =
      line + line;

  }


  /* =========================================================
     AROUND YOU COUNTS
  ========================================================= */

  function renderCounts(){

    const relevant =
      state.stories;


    const near =
      relevant.filter(
        article =>
          locationScore(article) >= 70
      ).length;


    const district =
      relevant.filter(
        article =>
          locationScore(article) >= 55
      ).length;


    const stateCount =
      relevant.filter(
        article =>
          locationScore(article) >= 30
      ).length;


    const set =
      (selector,value) => {

        const element =
          $(selector);

        if(element){

          element.textContent =
            value;

        }

      };


    set(
      "#nearCount",
      state.location
        ? near
        : "—"
    );


    set(
      "#districtCount",
      state.location
        ? district
        : "—"
    );


    set(
      "#stateCount",
      state.location
        ? stateCount
        : "—"
    );


    set(
      "#weatherLocation",
      locationText()
    );


    set(
      "#weatherCondition",
      locationDetail()
    );

  }


  /* =========================================================
     CONTROLS
  ========================================================= */

  function syncControls(){

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


  /* =========================================================
     LOAD ARTICLES
  ========================================================= */

  async function loadStories(){

    if(state.loading){

      return;

    }


    state.loading = true;

    setStatus(
      "Finding the signal…"
    );


    let data = null;


    /*
      PRODUCTION:

      articles.json is loaded first.

      This works on GitHub Pages
      and your custom domain.
    */

    try{

      const response =
        await fetch(
          `./articles.json?v=${Date.now()}`,
          {
            cache:"no-store"
          }
        );


      if(response.ok){

        data =
          await response.json();

      }

    }catch(error){

      console.warn(
        "articles.json unavailable",
        error
      );

    }


    /*
      OPTIONAL API FALLBACK
    */

    if(!data){

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

      }catch(error){

        console.warn(
          "API unavailable",
          error
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


    state.page = 1;

    state.loading = false;

    render();

  }


  /* =========================================================
     AUTOMATIC IP LOCATION
     NO BROWSER GPS
  ========================================================= */

  async function detectLocationSilently(){

    try{

      const response =
        await fetch(
          "https://ipapi.co/json/",
          {
            cache:"no-store"
          }
        );


      if(!response.ok){

        throw new Error(
          "IP location unavailable"
        );

      }


      const data =
        await response.json();


      const base = {

        country:
          data.country_name ||
          "India",

        state:
          data.region ||
          "",

        district:
          "",

        city:
          data.city ||
          "",

        taluk:
          "",

        locality:
          data.city ||
          "",

        latitude:
          Number(data.latitude) ||
          null,

        longitude:
          Number(data.longitude) ||
          null,

        source:
          "ip"

      };


      /*
        Better administrative
        location.
      */

      try{

        if(
          Number.isFinite(
            base.latitude
          ) &&
          Number.isFinite(
            base.longitude
          )
        ){

          const url =

            "https://api.bigdatacloud.net/data/" +

            "reverse-geocode-client" +

            "?latitude=" +

            encodeURIComponent(
              base.latitude
            ) +

            "&longitude=" +

            encodeURIComponent(
              base.longitude
            ) +

            "&localityLanguage=en";


          const reverse =
            await fetch(
              url,
              {
                cache:"no-store"
              }
            );


          if(reverse.ok){

            const geo =
              await reverse.json();


            const address =
              geo.address ||
              {};


            base.state =
              address.principalSubdivision ||
              base.state;


            base.city =
              address.city ||
              address.locality ||
              base.city;


            base.locality =
              address.locality ||
              address.village ||
              base.locality;


            const administrative =
              address
                ?.localityInfo
                ?.administrative ||
              [];


            const districtItem =
              administrative.find(
                item =>
                  /district/i.test(
                    item.description ||
                    ""
                  )
              );


            base.district =
              districtItem?.name ||
              address.county ||
              base.district;


            base.taluk =
              address.suburb ||
              address.municipality ||
              base.taluk;

          }

        }

      }catch(error){

        console.warn(
          "Reverse geocode unavailable",
          error
        );

      }


      state.location =
        base;


      safeWrite(
        "snippet24_location",
        base
      );


      if(
        Number.isFinite(
          base.latitude
        ) &&
        Number.isFinite(
          base.longitude
        )
      ){

        renderWeather(
          base.latitude,
          base.longitude
        );

      }


      renderCounts();

      render();

    }catch(error){

      console.warn(
        "Automatic location unavailable",
        error
      );


      const element =
        $("#weatherLocation");


      if(
        element &&
        !state.location
      ){

        element.textContent =
          "Your area";

      }

    }

  }


  /* =========================================================
     WEATHER
  ========================================================= */

  async function renderWeather(
    latitude,
    longitude
  ){

    if(
      !Number.isFinite(
        Number(latitude)
      ) ||
      !Number.isFinite(
        Number(longitude)
      )
    ){

      return;

    }


    try{

      const url =

        "https://api.open-meteo.com/v1/forecast" +

        "?latitude=" +

        encodeURIComponent(
          latitude
        ) +

        "&longitude=" +

        encodeURIComponent(
          longitude
        ) +

        "&current=temperature_2m,weather_code" +

        "&timezone=auto" +

        "&forecast_days=1";


      const response =
        await fetch(
          url,
          {
            cache:"no-store"
          }
        );


      if(!response.ok){

        return;

      }


      const data =
        await response.json();


      const temperature =
        Math.round(
          Number(
            data?.current
              ?.temperature_2m
          )
        );


      const code =
        Number(
          data?.current
            ?.weather_code
        );


      const weatherMap = {

        0:["☀️","Clear"],

        1:["🌤️","Mostly clear"],

        2:["⛅","Partly cloudy"],

        3:["☁️","Cloudy"],

        45:["🌫️","Foggy"],

        48:["🌫️","Foggy"],

        51:["🌦️","Drizzle"],

        53:["🌦️","Drizzle"],

        55:["🌧️","Drizzle"],

        61:["🌧️","Rain"],

        63:["🌧️","Rain"],

        65:["🌧️","Heavy rain"],

        71:["🌨️","Snow"],

        73:["🌨️","Snow"],

        75:["❄️","Snow"],

        80:["🌦️","Showers"],

        81:["🌦️","Showers"],

        82:["⛈️","Heavy showers"],

        95:["⛈️","Thunderstorm"],

        96:["⛈️","Thunderstorm"],

        99:["⛈️","Thunderstorm"]

      };


      const info =
        weatherMap[code] ||
        ["🌤️","Current weather"];


      const tempElement =
        $("#weatherTemp");


      if(tempElement){

        tempElement.textContent =
          Number.isFinite(
            temperature
          )

            ? `${temperature}°`

            : "--°";

      }


      const iconElement =
        $("#weatherIcon");


      if(iconElement){

        iconElement.textContent =
          info[0];

      }


      const conditionElement =
        $("#weatherCondition");


      if(conditionElement){

        conditionElement.textContent =
          info[1];

      }

    }catch(error){

      console.warn(
        "Weather unavailable",
        error
      );

    }

  }


  /* =========================================================
     SEARCH
  ========================================================= */

  function openSearch(){

    const overlay =
      $("#searchOverlay");


    if(!overlay){

      return;

    }


    overlay.hidden =
      false;


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

      overlay.hidden =
        true;

    }

  }


  function runSearch(query){

    const box =
      $("#searchResults");


    if(!box){

      return;

    }


    const q =
      String(query || "")
        .trim()
        .toLowerCase();


    if(!q){

      box.innerHTML =
        "";

      return;

    }


    const results =
      state.stories

        .filter(article => {

          const text = [

            titleOf(article),

            summaryOf(article),

            ...pointsOf(article),

            categoryOf(article),

            article.publisher,

            article.location

          ]

          .filter(Boolean)

          .join(" ")

          .toLowerCase();


          return text.includes(q);

        })

        .slice(0,20);


    if(!results.length){

      box.innerHTML = `

        <div class="search-result">

          No matching story yet.

        </div>

      `;

      return;

    }


    box.innerHTML =
      results.map(article => {

        const source =
          safeUrl(
            sourceOf(article)
          );


        const html = `

          <strong>
            ${esc(
              titleOf(article)
            )}
          </strong>

          <br>

          <small>
            ${esc(
              categoryOf(article)
            )}
          </small>

        `;


        if(source){

          return `

            <a
              class="search-result"
              href="${esc(source)}"
              target="_blank"
              rel="noopener noreferrer">

              ${html}

            </a>

          `;

        }


        return `

          <div class="search-result">

            ${html}

          </div>

        `;

      }).join("");

  }


  /* =========================================================
     LOCATION MODAL
  ========================================================= */

  function openLocationModal(){

    const location =
      state.location || {};


    const fields = {

      State:
        location.state || "",

      District:
        location.district || "",

      City:
        location.city || "",

      Taluk:
        location.taluk || "",

      Locality:
        location.locality || ""

    };


    Object.entries(fields)
      .forEach(
        ([key,value]) => {

          const element =
            $(
              "#manual" +
              key
            );


          if(element){

            element.value =
              value;

          }

        }
      );


    const modal =
      $("#locationModal");


    if(modal){

      modal.hidden =
        false;

      modal.setAttribute(
        "aria-hidden",
        "false"
      );

    }

  }


  function closeLocationModal(){

    const modal =
      $("#locationModal");


    if(modal){

      modal.hidden =
        true;

      modal.setAttribute(
        "aria-hidden",
        "true"
      );

    }

  }


  function saveManualLocation(){

    state.location = {

      country:"India",

      state:
        $("#manualState")
          ?.value
          .trim() ||
        "",

      district:
        $("#manualDistrict")
          ?.value
          .trim() ||
        "",

      city:
        $("#manualCity")
          ?.value
          .trim() ||
        "",

      taluk:
        $("#manualTaluk")
          ?.value
          .trim() ||
        "",

      locality:
        $("#manualLocality")
          ?.value
          .trim() ||
        "",

      source:"manual"

    };


    safeWrite(
      "snippet24_location",
      state.location
    );


    closeLocationModal();

    render();

  }


  /* =========================================================
     BIND EVENTS
  ========================================================= */

  function bind(){

    $$("[data-category]")
      .forEach(element => {

        element.addEventListener(
          "click",
          () => {

            const category =
              element.dataset.category;


            if(!category){

              return;

            }


            state.category =
              category;


            state.page =
              1;


            const mobileMenu =
              $("#mobileMenu");


            if(mobileMenu){

              mobileMenu.hidden =
                true;

            }


            render();


            $("#stories")
              ?.scrollIntoView({
                behavior:"smooth",
                block:"start"
              });

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


    $("#searchInput")
      ?.addEventListener(
        "input",
        event =>
          runSearch(
            event.target.value
          )
      );


    $("#searchOverlay")
      ?.addEventListener(
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


    $("#menuBtn")
      ?.addEventListener(
        "click",
        () => {

          const menu =
            $("#mobileMenu");


          if(!menu){

            return;

          }


          menu.hidden =
            !menu.hidden;


          $("#menuBtn")
            ?.setAttribute(
              "aria-expanded",
              String(
                !menu.hidden
              )
            );

        }
      );


    $("#changeLocationBtn")
      ?.addEventListener(
        "click",
        openLocationModal
      );


    $("#worldArrow")
      ?.addEventListener(
        "click",
        () => {

          $("#stories")
            ?.scrollIntoView({
              behavior:"smooth",
              block:"start"
            });

        }
      );


    [
      "nearCard",
      "districtCard",
      "stateCard"

    ].forEach(id => {

      $("#" + id)
        ?.addEventListener(
          "click",
          () => {

            $("#stories")
              ?.scrollIntoView({
                behavior:"smooth",
                block:"start"
              });

          }
        );

    });


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
        async () => {

          closeLocationModal();

          await detectLocationSilently();

        }
      );


    $("#catchupBtn")
      ?.addEventListener(
        "click",
        () => {

          state.category =
            "All";

          state.speed =
            60;

          state.page =
            1;

          render();

          $("#topStories")
            ?.scrollIntoView({
              behavior:"smooth",
              block:"start"
            });

        }
      );


    $("#viewAllBtn")
      ?.addEventListener(
        "click",
        () => {

          state.category =
            "All";

          state.page =
            1;

          render();

          $("#stories")
            ?.scrollIntoView({
              behavior:"smooth",
              block:"start"
            });

        }
      );


    $("#premiumBtn")
      ?.addEventListener(
        "click",
        () => {

          alert(
            "Snippet24 Premium — Deep Dive, expert perspective, data & context, what's next and ad-free reading."
          );

        }
      );

  }


  /* =========================================================
     START
  ========================================================= */

  bind();


  loadStories();


  /*
    If location already exists,
    immediately show weather.
  */

  if(
    state.location?.latitude &&
    state.location?.longitude
  ){

    renderWeather(
      state.location.latitude,
      state.location.longitude
    );

  }

  else{

    /*
      Silent IP detection.

      IMPORTANT:
      navigator.geolocation is NOT used.
      Therefore there is no browser
      location permission popup.
    */

    setTimeout(
      detectLocationSilently,
      300
    );

  }


})();