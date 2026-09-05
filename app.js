(() => {

  const state = {
    stories: [],
    category: "All",
    lang: localStorage.getItem("snippet24_lang") || "en",
    speed: 60
  };


  /* --------------------------------
     HELPERS
  -------------------------------- */

  const $ = selector =>
    document.querySelector(selector);

  const $$ = selector =>
    [...document.querySelectorAll(selector)];


  /* --------------------------------
     LANGUAGE / TITLE
  -------------------------------- */

  function getTitle(story) {
    return (
      story?.translations?.[state.lang]?.title ||
      story?.[state.lang]?.title ||
      story?.headline ||
      story?.title ||
      ""
    );
  }


  /* --------------------------------
     SUMMARY
  -------------------------------- */

  function getSummary(story) {
    return (
      story?.translations?.[state.lang]?.summary ||
      story?.[state.lang]?.summary ||
      story?.summary ||
      ""
    );
  }


  /* --------------------------------
     KEY POINTS
     JSON uses snippet_lines
  -------------------------------- */

  function getPoints(story) {

    const translated =
      story?.translations?.[state.lang]?.key_points;

    const languagePoints =
      story?.[state.lang]?.key_points;

    const snippetLines =
      story?.snippet_lines;

    const oldPoints =
      story?.key_points;

    return (
      translated ||
      languagePoints ||
      snippetLines ||
      oldPoints ||
      []
    );
  }


  /* --------------------------------
     CATEGORY
  -------------------------------- */

  function categoryOf(story) {

    const raw =
      story?.category ||
      story?.section ||
      "India";

    /*
      Existing JSON uses "In India"
      while homepage navigation uses "India".
    */

    if (raw === "In India") {
      return "India";
    }

    if (raw === "Business & Economy") {
      return "Business & Economy";
    }

    if (raw === "Tech & AI") {
      return "Tech & AI";
    }

    /*
      Some sports stories are currently
      stored under In India.
    */

    if (raw === "India") {

      const text = (
        getTitle(story) +
        " " +
        getSummary(story)
      ).toLowerCase();

      const sportsWords = [
        "cricket",
        "football",
        "badminton",
        "tennis",
        "hockey",
        "pickleball",
        "olympic",
        "athlete",
        "championship",
        "world cup",
        "tournament",
        "match",
        "shuttler",
        "medal",
        "wicket",
        "goal",
        "league",
        "sport"
      ];

      if (
        sportsWords.some(
          word => text.includes(word)
        )
      ) {
        return "Sports";
      }
    }

    return raw;
  }


  /* --------------------------------
     SOURCE
  -------------------------------- */

  function sourceOf(story) {

    return (
      story?.original_source_url ||
      story?.source_url ||
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
      story?.image_url ||
      story?.image ||
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
      Try backend first.
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
        data = await response.json();
      }

    } catch (error) {

      console.log(
        "API unavailable"
      );

    }


    /*
      Fallback to articles.json.
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
          data = await response.json();
        }

      } catch (error) {

        console.log(
          "articles.json unavailable"
        );

      }
    }


    /*
      Support multiple JSON structures.
    */

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


  /* --------------------------------
     FILTER
  -------------------------------- */

  function filtered() {

    return state.stories.filter(
      story => {

        /*
          English is always available.
          Other languages require a real
          translation in the JSON.
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


        const category =
          categoryOf(story);


        return (
          hasTranslation &&
          (
            state.category === "All" ||
            category === state.category
          )
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
      element.textContent = text;
    }

  }


  /* --------------------------------
     SECURITY
  -------------------------------- */

  function escapeHtml(value = "") {

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
     READING CONTENT
  -------------------------------- */

  function readingContent(story) {

    const title =
      getTitle(story);

    const points =
      getPoints(story);

    const summary =
      getSummary(story);


    /*
      10 SECOND
      Only the essential fact.
    */

    if (state.speed === 10) {

      return `
        <div class="reading-level ten-sec">
          <span class="reading-label">
            10 SEC · WHAT HAPPENED?
          </span>

          <p>
            ${escapeHtml(
              points[0] ||
              title
            )}
          </p>
        </div>
      `;

    }


    /*
      60 SECOND
      What happened + why it matters.
    */

    if (state.speed === 60) {

      return `
        <div class="reading-level sixty-sec">

          <span class="reading-label">
            60 SEC · WHY IT MATTERS
          </span>

          ${
            points.length
              ? `
                <ul class="key-points">
                  ${points
                    .slice(0, 3)
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
              : ""
          }

          ${
            summary
              ? `
                <div class="why">
                  <b>WHY IT MATTERS</b>
                  <p>
                    ${escapeHtml(summary)}
                  </p>
                </div>
              `
              : ""
          }

        </div>
      `;

    }


    /*
      3 MINUTE
      Bigger picture.
      
      IMPORTANT:
      Do not invent additional facts.
      Use only content available in JSON.
    */

    return `
      <div class="reading-level three-min">

        <span class="reading-label">
          3 MIN · BIGGER PICTURE
        </span>

        ${
          points.length
            ? `
              <div class="context-section">

                <h4>
                  WHAT HAPPENED
                </h4>

                <ul class="key-points">
                  ${points
                    .slice(0, 3)
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

              </div>
            `
            : ""
        }


        ${
          summary
            ? `
              <div class="context-section">

                <h4>
                  WHY IT MATTERS
                </h4>

                <p>
                  ${escapeHtml(summary)}
                </p>

              </div>
            `
            : ""
        }


        <div class="editorial-note">
          Rephrased from the original source
          for clarity.
        </div>

      </div>
    `;

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

    const signal =
      story?.signal ||
      (
        story?.breaking
          ? "BREAKING"
          : "IMPORTANT"
      );


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

    } else {

      imageHTML = `
        <div class="story-image"></div>
      `;

    }


    const sourceHTML =
      source
        ? `
          <div class="story-footer">

            <span class="editorial-note">
              Rephrased from the original
              source for clarity.
            </span>

            <a
              class="source-link"
              href="${escapeHtml(source)}"
              target="_blank"
              rel="noopener noreferrer"
            >
              Original source →
            </a>

          </div>
        `
        : `
          <div class="story-footer">

            <span class="editorial-note">
              Rephrased from the original
              source for clarity.
            </span>

          </div>
        `;


    return `

      <article class="story-card">

        ${imageHTML}

        <div class="story-body">

          <span class="signal-label">
            ${escapeHtml(signal)}
          </span>


          <h3>
            ${escapeHtml(
              title ||
              "Story title unavailable"
            )}
          </h3>


          <div class="story-meta">

            ${escapeHtml(
              categoryOf(story)
            )}

            ${
              story?.published_at
                ? " • " +
                  escapeHtml(
                    new Date(
                      story.published_at
                    ).toLocaleString()
                  )
                : ""
            }

          </div>


          ${readingContent(story)}


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

    } else {

      container.innerHTML = `

        <div class="empty">

          No published stories are
          available in

          <b>
            ${escapeHtml(state.lang)}
          </b>

          for this section yet.

        </div>

      `;

    }


    setStatus(
      stories.length
        ? `${stories.length} stories • updated now`
        : "No stories available yet."
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

    const items =
      stories.slice(0, 12);

    const ticker =
      $("#tickerTrack");


    if (!ticker) {
      return;
    }


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
      Duplicate stories for continuous ticker.
    */

    const combined =
      [...items, ...items];


    ticker.innerHTML =
      combined
        .map(
          story => `
            <span class="ticker-item">
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


    /*
      Categories
    */

    $$("[data-category]")
      .forEach(
        element => {

          element.classList.toggle(
            "active",
            element.dataset.category ===
            state.category
          );

        }
      );


    /*
      Languages
    */

    $$("[data-lang]")
      .forEach(
        element => {

          element.classList.toggle(
            "active",
            element.dataset.lang ===
            state.lang
          );

        }
      );


    /*
      Speed buttons
    */

    $$("[data-speed]")
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


    const languageSelect =
      $("#languageSelect");


    if (languageSelect) {

      languageSelect.value =
        state.lang;

    }

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


  $$("[data-category]")
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

  $$("[data-lang]")
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


  if (moreBtn) {

    moreBtn.addEventListener(
      "click",
      () => {

        const menu =
          $("#moreMenu");

        if (menu) {

          menu.classList.toggle(
            "show"
          );

        }

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

        setCategory("All");

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

        /*
          Catch Me Up starts with
          the 60-second experience.
        */

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

  $$("[data-speed]")
    .forEach(
      button => {

        button.addEventListener(
          "click",
          () => {

            const speed =
              Number(
                button.dataset.speed
              );


            if (
              ![10, 60, 180]
                .includes(speed)
            ) {
              return;
            }


            state.speed =
              speed;


            render();


            const signal =
              $("#signal");


            if (signal) {

              signal.scrollIntoView({
                behavior: "smooth",
                block: "start"
              });

            }

          }
        );

      }
    );


  /* --------------------------------
     SEARCH
  -------------------------------- */

  const searchBtn =
    $("#searchBtn");


  if (searchBtn) {

    searchBtn.addEventListener(
      "click",
      () => {

        const panel =
          $("#searchPanel");

        const input =
          $("#searchInput");


        if (panel) {

          panel.classList.add("show");

        }


        if (input) {

          input.focus();

        }

      }
    );

  }


  const closeSearch =
    $("#closeSearch");


  if (closeSearch) {

    closeSearch.addEventListener(
      "click",
      () => {

        const panel =
          $("#searchPanel");

        if (panel) {

          panel.classList.remove(
            "show"
          );

        }

      }
    );

  }


  const searchPanel =
    $("#searchPanel");


  if (searchPanel) {

    searchPanel.addEventListener(
      "click",
      event => {

        if (
          event.target.id ===
          "searchPanel"
        ) {

          event.currentTarget
            .classList.remove(
              "show"
            );

        }

      }
    );

  }


  const searchInput =
    $("#searchInput");


  if (searchInput) {

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

                const title =
                  getTitle(story)
                    .toLowerCase();

                const summary =
                  getSummary(story)
                    .toLowerCase();

                const points =
                  getPoints(story)
                    .join(" ")
                    .toLowerCase();


                return (
                  title.includes(query) ||
                  summary.includes(query) ||
                  points.includes(query)
                );

              }
            )
            .slice(0, 8);


        const resultsContainer =
          $("#searchResults");


        if (!resultsContainer) {
          return;
        }


        resultsContainer.innerHTML =
          query
            ? results
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

                      <div class="search-result">

                        ${escapeHtml(
                          getTitle(story)
                        )}

                      </div>

                    `;

                  }
                )
                .join("")
            : "";

      }
    );

  }


  /* --------------------------------
     START
  -------------------------------- */

  loadStories();

})();