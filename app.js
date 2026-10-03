(() => {

  "use strict";


  /* =========================================
     STATE
  ========================================== */

  const state = {

    stories: [],

    topic: "For You",

    language:
      localStorage.getItem("snippet24_language")
      || "en",

    saved:
      JSON.parse(
        localStorage.getItem("snippet24_saved")
        || "[]"
      ),

    liked:
      JSON.parse(
        localStorage.getItem("snippet24_liked")
        || "[]"
      ),

    location:
      localStorage.getItem("snippet24_location")
      || "Around You"

  };


  const REFRESH_INTERVAL =
    5 * 60 * 1000;


  /* =========================================
     DOM
  ========================================== */

  const $ = selector =>
    document.querySelector(selector);

  const $$ = selector =>
    [...document.querySelectorAll(selector)];


  /* =========================================
     TRANSLATIONS
  ========================================== */

  const UI = {

    en: {
      forYou: "For You",
      around: "Around You",
      liveFeed: "LIVE FEED",
      howAffects: "HOW IT AFFECTS YOU",
      source: "Source",
      stories: "stories",
      updated: "Updated",
      search: "Search stories, topics, places..."
    },

    ta: {
      forYou: "உங்களுக்காக",
      around: "உங்களைச் சுற்றி",
      liveFeed: "நேரலை செய்தி",
      howAffects: "உங்களை இது எப்படி பாதிக்கும்",
      source: "ஆதாரம்",
      stories: "செய்திகள்",
      updated: "புதுப்பிக்கப்பட்டது",
      search: "செய்திகள், தலைப்புகள், இடங்களைத் தேடுங்கள்..."
    },

    hi: {
      forYou: "आपके लिए",
      around: "आपके आसपास",
      liveFeed: "लाइव फीड",
      howAffects: "आप पर इसका असर",
      source: "स्रोत",
      stories: "समाचार",
      updated: "अपडेट",
      search: "समाचार, विषय और स्थान खोजें..."
    }

  };


  function t(key) {

    return (
      UI[state.language]?.[key]
      ||
      UI.en[key]
      ||
      key
    );

  }


  /* =========================================
     TEXT HELPERS
  ========================================== */

  function getLocalized(story, field) {

    return (

      story?.translations?.[
        state.language
      ]?.[field]

      ||

      story?.[state.language]?.[field]

      ||

      story?.[field]

      ||

      ""

    );

  }


  function getTitle(story) {

    return getLocalized(
      story,
      "title"
    );

  }


  function getSummary(story) {

    return getLocalized(
      story,
      "summary"
    );

  }


  function getImpact(story) {

    return (

      getLocalized(
        story,
        "impact"
      )

      ||

      story.how_it_affects_you

      ||

      "No immediate direct impact identified."

    );

  }


  function getCategory(story) {

    return (
      story.category
      ||
      "India"
    );

  }


  function getSource(story) {

    return (
      story.publisher
      ||
      story.source
      ||
      "SNIPPET24 Sources"
    );

  }


  function getURL(story) {

    return (
      story.source_url
      ||
      story.url
      ||
      "#"
    );

  }


  function getImage(story) {

    return (
      story.image_url
      ||
      story.image
      ||
      ""
    );

  }


  function getPublishedTime(story) {

    const value =
      story.published_at
      ||
      story.updated_at
      ||
      story.created_at;

    if (!value) {
      return "";
    }

    const date =
      new Date(value);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return "";
    }

    const diff =
      Date.now()
      -
      date.getTime();

    const minutes =
      Math.floor(
        diff / 60000
      );

    if (minutes < 1) {
      return "Just now";
    }

    if (minutes < 60) {
      return `${minutes} min ago`;
    }

    const hours =
      Math.floor(
        minutes / 60
      );

    if (hours < 24) {
      return `${hours} hr ago`;
    }

    return date.toLocaleDateString(
      state.language,
      {
        day: "numeric",
        month: "short"
      }
    );

  }


  /* =========================================
     SECURITY
  ========================================== */

  function escapeHTML(value) {

    return String(value ?? "")

      .replaceAll("&", "&amp;")

      .replaceAll("<", "&lt;")

      .replaceAll(">", "&gt;")

      .replaceAll('"', "&quot;")

      .replaceAll(
        "'",
        "&#039;"
      );

  }


  function safeURL(value) {

    try {

      const url =
        new URL(
          value || "#",
          window.location.href
        );

      if (
        url.protocol === "http:"
        ||
        url.protocol === "https:"
      ) {

        return url.href;

      }

    } catch (_) {}

    return "#";

  }


  /* =========================================
     API
  ========================================== */

  async function loadStories() {

    setLoading(true);

    let data = null;


    /*
      FIRST:
      Real backend
    */

    try {

      const response =
        await fetch(
          "/api/stories",
          {
            method: "GET",
            cache: "no-store",
            headers: {
              "Accept":
                "application/json"
            }
          }
        );


      if (response.ok) {

        data =
          await response.json();

      }

    } catch (error) {

      console.log(
        "Live API unavailable",
        error
      );

    }


    /*
      SECOND:
      Local demo data
    */

    if (!data) {

      try {

        const response =
          await fetch(
            "/articles.json",
            {
              cache: "no-store"
            }
          );

        if (response.ok) {

          data =
            await response.json();

        }

      } catch (error) {

        console.log(
          "Demo data unavailable",
          error
        );

      }

    }


    if (
      Array.isArray(data)
    ) {

      state.stories =
        data;

    }

    else if (
      Array.isArray(data?.stories)
    ) {

      state.stories =
        data.stories;

    }

    else if (
      Array.isArray(data?.articles)
    ) {

      state.stories =
        data.articles;

    }

    else {

      state.stories = [];

    }


    /*
      LIFO:
      newest first
    */

    state.stories.sort(
      (a, b) => {

        const aTime =
          new Date(
            a.published_at
            ||
            a.updated_at
            ||
            a.created_at
            ||
            0
          ).getTime();

        const bTime =
          new Date(
            b.published_at
            ||
            b.updated_at
            ||
            b.created_at
            ||
            0
          ).getTime();

        return bTime - aTime;

      }
    );


    render();

    updateLastUpdated();

    setLoading(false);

  }


  /* =========================================
     FILTER
  ========================================== */

  function filteredStories() {

    if (
      state.topic === "For You"
    ) {

      return state.stories;

    }


    return state.stories.filter(
      story => {

        const category =
          String(
            getCategory(story)
          ).toLowerCase();

        const wanted =
          state.topic.toLowerCase();

        if (
          wanted === "technology"
        ) {

          return (
            category.includes("tech")
            ||
            category.includes("ai")
          );

        }

        return (
          category.includes(wanted)
        );

      }
    );

  }


  /* =========================================
     RENDER
  ========================================== */

  function render() {

    renderFeed();

    renderAround();

    updateLanguageUI();

    updateCounters();

  }


  /* =========================================
     FEED
  ========================================== */

  function renderFeed() {

    const container =
      $("#feed");

    const stories =
      filteredStories();


    if (!stories.length) {

      container.innerHTML = `

        <div class="loading">

          No stories available yet.

        </div>

      `;

      return;

    }


    container.innerHTML =
      stories
        .map(
          renderStory
        )
        .join("");

  }


  function renderStory(story) {

    const id =
      story.id
      ||
      story.story_id
      ||
      story.url
      ||
      Math.random()
        .toString(36)
        .slice(2);


    const title =
      getTitle(story);

    const summary =
      getSummary(story);

    const impact =
      getImpact(story);

    const category =
      getCategory(story);

    const image =
      getImage(story);

    const source =
      getSource(story);

    const sourceURL =
      safeURL(
        getURL(story)
      );

    const time =
      getPublishedTime(story);

    const isSaved =
      state.saved.includes(
        String(id)
      );

    const isLiked =
      state.liked.includes(
        String(id)
      );


    return `

      <article
        class="story-card"
        data-story-id="${escapeHTML(id)}"
      >

        ${
          image
          ?
          `
          <img
            class="story-image"
            src="${safeURL(image)}"
            alt=""
            loading="lazy"
            onerror="this.style.display='none'"
          >
          `
          :
          ""
        }


        <div class="story-body">

          <div class="story-topline">

            <span class="story-category">
              ${escapeHTML(category)}
            </span>

            <span>•</span>

            <span class="story-time">
              ${escapeHTML(time)}
            </span>

          </div>


          <h3 class="story-title">

            ${escapeHTML(title)}

          </h3>


          <p class="story-summary">

            ${escapeHTML(summary)}

          </p>


          <div class="impact">

            <div class="impact-label">

              👤 ${escapeHTML(
                t("howAffects")
              )}

            </div>

            <p>

              ${escapeHTML(impact)}

            </p>

          </div>


          <div class="story-source">

            ${escapeHTML(
              t("source")
            )}:

            <a
              href="${sourceURL}"
              target="_blank"
              rel="noopener noreferrer"
            >
              ${escapeHTML(source)}
            </a>

          </div>


          <div class="story-actions">

            <button
              data-action="like"
              data-id="${escapeHTML(id)}"
              aria-label="Like"
            >
              ${isLiked ? "❤️" : "♡"}
            </button>


            <button
              data-action="comment"
              data-id="${escapeHTML(id)}"
            >
              💬
            </button>


            <button
              data-action="share"
              data-id="${escapeHTML(id)}"
            >
              ↗
            </button>


            <button
              data-action="save"
              data-id="${escapeHTML(id)}"
              aria-label="Save"
            >
              ${isSaved ? "🔖" : "♡"}
            </button>

          </div>

        </div>

      </article>

    `;

  }


  /* =========================================
     AROUND YOU
  ========================================== */

  function renderAround() {

    $("#locationText").textContent =
      state.location;


    const localStories =
      state.stories
        .filter(
          story => {

            const location =
              String(
                story.location
                ||
                ""
              ).toLowerCase();

            return (
              location
              &&
              (
                location.includes(
                  state.location.toLowerCase()
                )
                ||
                location === "local"
                ||
                location === "nearby"
              )
            );

          }
        )
        .slice(0, 12);


    const stories =
      localStories.length
      ?
      localStories
      :
      state.stories.slice(0, 8);


    $("#aroundFeed").innerHTML =
      stories
        .map(
          story => `

            <article
              class="around-card"
              data-id="${escapeHTML(
                story.id || ""
              )}"
            >

              <div class="tag">
                ${escapeHTML(
                  getCategory(story)
                )}
              </div>

              <h3>
                ${escapeHTML(
                  getTitle(story)
                )}
              </h3>

              <p>
                ${escapeHTML(
                  getSummary(story)
                )}
              </p>

            </article>

          `
        )
        .join("");

  }


  /* =========================================
     INTERACTION
  ========================================== */

  document.addEventListener(
    "click",
    event => {

      const button =
        event.target.closest(
          "[data-action]"
        );

      if (!button) {
        return;
      }


      const action =
        button.dataset.action;

      const id =
        String(
          button.dataset.id
        );


      if (action === "like") {

        toggleArray(
          state.liked,
          id
        );

        localStorage.setItem(
          "snippet24_liked",
          JSON.stringify(
            state.liked
          )
        );

        render();

      }


      if (action === "save") {

        toggleArray(
          state.saved,
          id
        );

        localStorage.setItem(
          "snippet24_saved",
          JSON.stringify(
            state.saved
          )
        );

        render();

      }


      if (action === "share") {

        shareStory(id);

      }


      if (action === "comment") {

        openStory(id);

      }

    }
  );


  function toggleArray(
    array,
    value
  ) {

    const index =
      array.indexOf(value);

    if (index >= 0) {

      array.splice(
        index,
        1
      );

    } else {

      array.push(value);

    }

  }


  /* =========================================
     SHARE
  ========================================== */

  async function shareStory(id) {

    const story =
      state.stories.find(
        item =>
          String(
            item.id
            ||
            item.story_id
            ||
            item.url
          )
          ===
          String(id)
      );


    if (!story) {
      return;
    }


    const title =
      getTitle(story);


    if (
      navigator.share
    ) {

      try {

        await navigator.share({

          title:
            `SNIPPET24 — ${title}`,

          text:
            `${title}\n\n${getSummary(story)}`,

          url:
            getURL(story)

        });

      } catch (_) {}

      return;

    }


    try {

      await navigator.clipboard.writeText(
        `${title}\n${getURL(story)}`
      );

      alert(
        "Story link copied."
      );

    } catch (_) {

      alert(
        getURL(story)
      );

    }

  }


  /* =========================================
     OPEN STORY
  ========================================== */

  function openStory(id) {

    const story =
      state.stories.find(
        item =>
          String(
            item.id
            ||
            item.story_id
            ||
            item.url
          )
          ===
          String(id)
      );


    if (!story) {
      return;
    }


    $("#modalContent").innerHTML = `

      <div class="story-category">

        ${escapeHTML(
          getCategory(story)
        )}

      </div>


      <h2>

        ${escapeHTML(
          getTitle(story)
        )}

      </h2>


      <p class="story-summary">

        ${escapeHTML(
          getSummary(story)
        )}

      </p>


      <div class="impact">

        <div class="impact-label">

          👤 ${escapeHTML(
            t("howAffects")
          )}

        </div>

        <p>

          ${escapeHTML(
            getImpact(story)
          )}

        </p>

      </div>


      <p class="story-source">

        ${escapeHTML(
          t("source")
        )}:

        <a
          href="${safeURL(
            getURL(story)
          )}"
          target="_blank"
          rel="noopener noreferrer"
        >
          ${escapeHTML(
            getSource(story)
          )}
        </a>

      </p>

    `;


    $("#storyModal").hidden =
      false;

  }


  /* =========================================
     TOPICS
  ========================================== */

  $$(".topic").forEach(
    button => {

      button.addEventListener(
        "click",
        () => {

          $$(".topic")
            .forEach(
              item =>
                item.classList.remove(
                  "active"
                )
            );


          button.classList.add(
            "active"
          );


          state.topic =
            button.dataset.topic;


          $("#feedTitle")
            .textContent =
              state.topic;


          renderFeed();

          window.scrollTo({
            top:
              document.querySelector(
                ".feed-section"
              ).offsetTop - 110,

            behavior:
              "smooth"
          });

        }
      );

    }
  );


  /* =========================================
     LANGUAGE
  ========================================== */

  $("#languageBtn")
    .addEventListener(
      "click",
      () => {

        const panel =
          $("#languagePanel");

        panel.hidden =
          !panel.hidden;

      }
    );


  $$(
    "[data-language]"
  ).forEach(
    button => {

      button.addEventListener(
        "click",
        () => {

          state.language =
            button.dataset.language;


          localStorage.setItem(
            "snippet24_language",
            state.language
          );


          $("#languagePanel")
            .hidden = true;


          updateLanguageUI();

          render();

        }
      );

    }
  );


  function updateLanguageUI() {

    $("#languageBtn")
      .textContent =
        state.language
          .toUpperCase();


    $("#searchInput")
      .placeholder =
        t("search");

  }


  /* =========================================
     SEARCH
  ========================================== */

  $("#searchBtn")
    .addEventListener(
      "click",
      () => {

        $("#searchPanel")
          .hidden = false;

        $("#searchInput")
          .focus();

      }
    );


  $("#closeSearch")
    .addEventListener(
      "click",
      () => {

        $("#searchPanel")
          .hidden = true;

      }
    );


  $("#searchInput")
    .addEventListener(
      "input",
      event => {

        const query =
          event.target.value
            .trim()
            .toLowerCase();


        if (!query) {

          state.topic =
            "For You";

          renderFeed();

          return;

        }


        const results =
          state.stories.filter(
            story => {

              const text = [

                getTitle(story),

                getSummary(story),

                getCategory(story),

                story.location

              ]
                .filter(Boolean)
                .join(" ")
                .toLowerCase();


              return text.includes(
                query
              );

            }
          );


        $("#feed").innerHTML =
          results.length
          ?
          results
            .map(
              renderStory
            )
            .join("")
          :
          `

            <div class="loading">

              No matching stories found.

            </div>

          `;

      }
    );


  /* =========================================
     REFRESH
  ========================================== */

  $("#refreshBtn")
    .addEventListener(
      "click",
      () => {

        loadStories();

      }
    );


  setInterval(
    () => {

      loadStories();

    },
    REFRESH_INTERVAL
  );


  /* =========================================
     CATCH ME UP
  ========================================== */

  $("#catchUpBtn")
    .addEventListener(
      "click",
      () => {

        const stories =
          state.stories
            .slice(0, 10);


        if (!stories.length) {
          return;
        }


        $("#modalContent").innerHTML = `

          <div class="eyebrow">
            SNIPPET24 AI
          </div>

          <h2>
            Catch Me Up
          </h2>

          <p class="story-summary">

            Here are the latest things worth knowing.

          </p>

          ${

            stories
              .map(
                story => `

                  <div
                    style="
                      padding:14px 0;
                      border-bottom:1px solid #292929;
                    "
                  >

                    <strong>

                      ${escapeHTML(
                        getTitle(story)
                      )}

                    </strong>

                    <p
                      style="
                        color:#aaa;
                        font-size:12px;
                        line-height:1.5;
                      "
                    >

                      ${escapeHTML(
                        getSummary(story)
                      )}

                    </p>

                  </div>

                `
              )
              .join("")

          }

        `;


        $("#storyModal")
          .hidden = false;

      }
    );


  /* =========================================
     MODAL
  ========================================== */

  $("#modalClose")
    .addEventListener(
      "click",
      () => {

        $("#storyModal")
          .hidden = true;

      }
    );


  $("#storyModal")
    .addEventListener(
      "click",
      event => {

        if (
          event.target.id
          ===
          "storyModal"
        ) {

          $("#storyModal")
            .hidden = true;

        }

      }
    );


  /* =========================================
     LOCATION
  ========================================== */

  $("#locationBtn")
    .addEventListener(
      "click",
      () => {

        const location =
          prompt(
            "Enter your city or area:"
          );


        if (
          location
          &&
          location.trim()
        ) {

          state.location =
            location.trim();


          localStorage.setItem(
            "snippet24_location",
            state.location
          );


          renderAround();

        }

      }
    );


  /* =========================================
     COUNTERS
  ========================================== */

  function updateCounters() {

    const count =
      filteredStories().length;


    $("#storyCounter")
      .textContent =
        `${count} ${t("stories")}`;

  }


  function updateLastUpdated() {

    const now =
      new Date();


    $("#lastUpdated")
      .textContent =
        `${t("updated")} ${
          now.toLocaleTimeString(
            [],
            {
              hour: "numeric",
              minute: "2-digit"
            }
          )
        }`;

  }


  function setLoading(
    loading
  ) {

    $("#loading")
      .style.display =
        loading
        ?
        "block"
        :
        "none";

  }


  /* =========================================
     START
  ========================================== */

  updateLanguageUI();

  loadStories();


})();