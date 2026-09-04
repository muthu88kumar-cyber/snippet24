(() => {
  "use strict";

  const state = {
    stories: [],
    category: "All",
    lang: localStorage.getItem("snippet24_lang") || "en",
    speed: 60
  };

  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];

  /* --------------------------------
     LANGUAGE DATA
  -------------------------------- */

  function languageData(story) {
    return (
      story?.translations?.[state.lang] ||
      story?.[state.lang] ||
      {}
    );
  }

  function getTitle(story) {
    const translated = languageData(story);

    return (
      translated.title ||
      translated.headline ||
      story?.title ||
      story?.headline ||
      ""
    );
  }

  function getSummary(story) {
    const translated = languageData(story);

    return (
      translated.summary ||
      story?.summary ||
      ""
    );
  }

  function getPoints(story) {
    const translated = languageData(story);

    if (Array.isArray(translated.key_points)) {
      return translated.key_points;
    }

    if (Array.isArray(story?.key_points)) {
      return story.key_points;
    }

    if (Array.isArray(translated.snippet_lines)) {
      return translated.snippet_lines;
    }

    if (Array.isArray(story?.snippet_lines)) {
      return story.snippet_lines;
    }

    return [];
  }

  /* --------------------------------
     CATEGORY
  -------------------------------- */

  function categoryOf(story) {

    const raw =
      story?.category ||
      story?.section ||
      "In India";

    /*
      Your JSON uses:
      "In India"

      Your website displays:
      "India"
    */

    if (raw === "In India") {

      const text = [
        story?.headline,
        story?.snippet,
        story?.summary
      ]
        .join(" ")
        .toLowerCase();

      /*
        Some sports stories are currently
        stored under "In India".
      */

      const sportsTerms = [
        "sport",
        "sports",
        "cricket",
        "football",
        "soccer",
        "badminton",
        "tennis",
        "hockey",
        "pickleball",
        "olympic",
        "paralympic",
        "athlete",
        "championship",
        "world cup",
        "tournament",
        "match",
        "shuttler",
        "medal",
        "wicket",
        "goal",
        "league"
      ];

      if (
        sportsTerms.some(term =>
          text.includes(term)
        )
      ) {
        return "Sports";
      }

      return "India";
    }

    return raw;
  }

  /* --------------------------------
     SOURCE
  -------------------------------- */

  function sourceOf(story) {

    return (
      story?.source_url ||
      story?.original_source_url ||
      story?.original_url ||
      story?.url ||
      ""
    );
  }

  /* --------------------------------
     IMAGE
  -------------------------------- */

  function imageOf(story) {

    return (
      story?.ai_image_url ||
      story?.image ||
      story?.image_url ||
      story?.ai_image ||
      ""
    );
  }

  /* --------------------------------
     LOAD STORIES
  -------------------------------- */

  async function loadStories() {

    setStatus("Finding the signal…");

    let data = null;

    /*
      First try backend API.
    */

    try {

      const response =
        await fetch(
          "./api/stories",
          {
            cache: "no-store"
          }
        );

      if (response.ok) {

        data =
          await response.json();

      }

    }
    catch (error) {

      console.log(
        "API unavailable"
      );

    }

    /*
      If backend is unavailable,
      use articles.json.
    */

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

      }
      catch (error) {

        console.log(
          "articles.json unavailable"
        );

      }

    }

    /*
      Support several JSON structures.
    */

    if (Array.isArray(data)) {

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

    render();

  }

  /* --------------------------------
     FILTER
  -------------------------------- */

  function filtered() {

    return state.stories.filter(
      story => {

        /*
          English is always available.

          Other languages are shown only
          when an actual translation exists.
        */

        const hasTranslation =
          state.lang === "en" ||
          !!(
            story?.translations?.[
              state.lang
            ] ||
            story?.[
              state.lang
            ]
          );

        if (!hasTranslation) {
          return false;
        }

        const category =
          categoryOf(story);

        return (
          state.category === "All" ||
          category === state.category
        );

      }
    );

  }

  /* --------------------------------
     STATUS
  -------------------------------- */

  function setStatus(text) {

    const element =
      $("#status");

    if (element) {

      element.textContent =
        text;

    }

  }

  /* --------------------------------
     SECURITY
  -------------------------------- */

  function escapeHtml(
    value = ""
  ) {

    return String(value)
      .replace(
        /[&<>"']/g,
        character => ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;"
        }[character])
      );

  }

  /* --------------------------------
     READING MODE
  -------------------------------- */

  function readingContent(story) {

    const points =
      getPoints(story);

    const summary =
      getSummary(story);

    /*
      Current articles.json contains:

      headline
      snippet_lines
      summary

      It does not currently contain
      separate 10 SEC / 60 SEC / 3 MIN
      article bodies.

      Therefore we only display content
      actually present in the JSON.
    */

    if (state.speed === 10) {

      return {
        points: points.slice(0, 1),
        summary: ""
      };

    }

    if (state.speed === 180) {

      return {
        points: points.slice(0, 3),
        summary: summary
      };

    }

    /*
      Default = 60 seconds
    */

    return {
      points: points.slice(0, 3),
      summary: summary
    };

  }

  /* --------------------------------
     STORY CARD
  -------------------------------- */

  function storyCard(story) {

    const title =
      getTitle(story);

    const source =
      sourceOf(story);

    const image =
      imageOf(story);

    const reading =
      readingContent(story);

    const signal =
      story?.signal ||
      (
        story?.breaking
          ? "BREAKING"
          : "IMPORTANT"
      );

    /* IMAGE */

    let imageHTML;

    if (image) {

      imageHTML = `

        <img
          class="story-image"
          src="${escapeHtml(image)}"
          alt=""
          loading="lazy"
          onerror="this.style.display='none'"
        >

      `;

    }

    else {

      imageHTML = `

        <div
          class="story-image">
        </div>

      `;

    }

    /* KEY POINTS */

    const pointsHTML =
      reading.points.length

      ?

      `

        <ul class="key-points">

          ${reading.points
            .map(
              point => `
                <li>
                  ${escapeHtml(point)}
                </li>
              `
            )
            .join("")
          }

        </ul>

      `

      :

      "";

    /* SUMMARY */

    const summaryHTML =
      reading.summary

      ?

      `

        <div class="why">

          <b>
            WHY IT MATTERS
          </b>

          <br>

          ${escapeHtml(
            reading.summary
          )}

        </div>

      `

      :

      "";

    /* SOURCE */

    const sourceHTML =
      source

      ?

      `

        <a
          class="source-link"
          href="${escapeHtml(source)}"
          target="_blank"
          rel="noopener noreferrer"
        >

          Original source →

        </a>

      `

      :

      "";

    /* DATE */

    const published =
      story?.published_at
        ?

        " • " +
        new Date(
          story.published_at
        ).toLocaleString()

        :

        "";

    return `

      <article
        class="story-card"
      >

        ${imageHTML}

        <div
          class="story-body"
        >

          <span
            class="signal-label"
          >

            ${escapeHtml(
              signal
            )}

          </span>


          <h3>

            ${escapeHtml(
              title ||
              "Story title unavailable"
            )}

          </h3>


          <div
            class="story-meta"
          >

            ${escapeHtml(
              categoryOf(story)
            )}

            ${escapeHtml(
              published
            )}

          </div>


          ${pointsHTML}


          ${summaryHTML}


          ${sourceHTML}

        </div>

      </article>

    `;

  }

  /* --------------------------------
     RENDER
  -------------------------------- */

  function render() {

    const stories =
      filtered();

    const container =
      $("#stories");

    if (!container) {
      return;
    }

    if (stories.length) {

      container.innerHTML =
        stories
          .map(storyCard)
          .join("");

    }

    else {

      container.innerHTML = `

        <div class="empty">

          No published stories are
          available in

          <b>
            ${escapeHtml(
              state.lang
            )}
          </b>

          for this section yet.

        </div>

      `;

    }

    setStatus(

      stories.length

        ?

        `${stories.length}
         stories • updated now`

        :

        "No stories available yet."

    );

    renderTicker(
      stories.length
        ? stories
        : state.stories
    );

    syncControls();

  }

  /* --------------------------------
     LIVE WIRE
  -------------------------------- */

  function renderTicker(stories) {

    const ticker =
      $("#tickerTrack");

    if (!ticker) {
      return;
    }

    const items =
      stories.slice(0, 12);

    if (!items.length) {

      ticker.innerHTML = `

        <span>

          Live Wire will appear
          when stories are published.

        </span>

      `;

      return;

    }

    /*
      Duplicate stories so the
      ticker can move continuously.
    */

    const combined =
      [
        ...items,
        ...items
      ];

    ticker.innerHTML =
      combined
        .map(
          story => `

            <span
              class="ticker-item"
            >

              ${escapeHtml(
                getTitle(story)
              )}

            </span>

          `
        )
        .join("");

  }

  /* --------------------------------
     ACTIVE CONTROLS
  -------------------------------- */

  function syncControls() {

    $$(
      "[data-category]"
    )
      .forEach(
        element => {

          element.classList.toggle(

            "active",

            element.dataset.category ===
            state.category

          );

        }
      );


    $$(
      "[data-lang]"
    )
      .forEach(
        element => {

          element.classList.toggle(

            "active",

            element.dataset.lang ===
            state.lang

          );

        }
      );


    const languageSelect =
      $("#languageSelect");

    if (languageSelect) {

      languageSelect.value =
        state.lang;

    }


    $$(
      "[data-speed]"
    )
      .forEach(
        element => {

          element.classList.toggle(

            "active",

            Number(
              element.dataset.speed
            ) === state.speed

          );

        }
      );

  }

  /* --------------------------------
     CATEGORY
  -------------------------------- */

  function setCategory(category) {

    state.category =
      category;

    const signal =
      $("#signal");

    if (signal) {

      signal.scrollIntoView({

        behavior: "smooth",

        block: "start"

      });

    }

    render();

  }


  $$(
    "[data-category]"
  )
    .forEach(
      element => {

        element.addEventListener(
          "click",
          event => {

            event.preventDefault();

            setCategory(
              element.dataset.category
            );

          }
        );

      }
    );

  /* --------------------------------
     LANGUAGE BUTTONS
  -------------------------------- */

  $$(
    "[data-lang]"
  )
    .forEach(
      element => {

        element.addEventListener(
          "click",
          () => {

            state.lang =
              element.dataset.lang;

            localStorage.setItem(
              "snippet24_lang",
              state.lang
            );

            render();

          }
        );

      }
    );

  /* --------------------------------
     LANGUAGE DROPDOWN
  -------------------------------- */

  const languageSelect =
    $("#languageSelect");

  if (languageSelect) {

    languageSelect.addEventListener(
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

  }

  /* --------------------------------
     MORE MENU
  -------------------------------- */

  const moreBtn =
    $("#moreBtn");

  const moreMenu =
    $("#moreMenu");

  if (
    moreBtn &&
    moreMenu
  ) {

    moreBtn.addEventListener(
      "click",
      () => {

        moreMenu.classList.toggle(
          "show"
        );

      }
    );

  }

  /* --------------------------------
     VIEW ALL
  -------------------------------- */

  const viewAllBtn =
    $("#viewAllBtn");

  if (viewAllBtn) {

    viewAllBtn.addEventListener(
      "click",
      () => {

        setCategory(
          "All"
        );

      }
    );

  }

  /* --------------------------------
     REFRESH
  -------------------------------- */

  const refreshBtn =
    $("#refreshBtn");

  if (refreshBtn) {

    refreshBtn.addEventListener(
      "click",
      loadStories
    );

  }

  /* --------------------------------
     CATCH ME UP
  -------------------------------- */

  const catchupBtn =
    $("#catchupBtn");

  if (catchupBtn) {

    catchupBtn.addEventListener(
      "click",
      () => {

        state.category =
          "All";

        state.speed =
          60;

        const signal =
          $("#signal");

        if (signal) {

          signal.scrollIntoView({

            behavior: "smooth",

            block: "start"

          });

        }

        render();

      }
    );

  }

  /* --------------------------------
     SPEED BUTTONS
  -------------------------------- */

  $$(
    "[data-speed]"
  )
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            state.speed =
              Number(
                button.dataset.speed
              ) || 60;

            const signal =
              $("#signal");

            if (signal) {

              signal.scrollIntoView({

                behavior: "smooth",

                block: "start"

              });

            }

            render();

          }
        );

      }
    );

  /* --------------------------------
     SEARCH
  -------------------------------- */

  const searchBtn =
    $("#searchBtn");

  const searchPanel =
    $("#searchPanel");

  const searchInput =
    $("#searchInput");

  const closeSearch =
    $("#closeSearch");

  const searchResults =
    $("#searchResults");


  if (
    searchBtn &&
    searchPanel &&
    searchInput
  ) {

    searchBtn.addEventListener(
      "click",
      () => {

        searchPanel.classList.add(
          "show"
        );

        searchInput.focus();

      }
    );

  }


  if (
    closeSearch &&
    searchPanel
  ) {

    closeSearch.addEventListener(
      "click",
      () => {

        searchPanel.classList.remove(
          "show"
        );

      }
    );

  }


  if (searchPanel) {

    searchPanel.addEventListener(
      "click",
      event => {

        if (
          event.target.id ===
          "searchPanel"
        ) {

          searchPanel.classList.remove(
            "show"
          );

        }

      }
    );

  }


  if (
    searchInput &&
    searchResults
  ) {

    searchInput.addEventListener(
      "input",
      event => {

        const query =
          event.target.value
            .trim()
            .toLowerCase();


        const results =
          state.stories

            .filter(
              story => {

                const searchable = [

                  getTitle(story),

                  getSummary(story),

                  ...getPoints(story)

                ]
                  .join(" ")
                  .toLowerCase();

                return searchable.includes(
                  query
                );

              }
            )

            .slice(0, 8);


        searchResults.innerHTML =
          query

            ?

            results
              .map(
                story => {

                  const source =
                    sourceOf(story);

                  if (source) {

                    return `

                      <a
                        class="search-result"
                        href="${escapeHtml(source)}"
                        target="_blank"
                        rel="noopener noreferrer"
                      >

                        ${escapeHtml(
                          getTitle(story)
                        )}

                      </a>

                    `;

                  }

                  return `

                    <div
                      class="search-result"
                    >

                      ${escapeHtml(
                        getTitle(story)
                      )}

                    </div>

                  `;

                }
              )
              .join("")

            :

            "";

      }
    );

  }

  /* --------------------------------
     START
  -------------------------------- */

  loadStories();

})();