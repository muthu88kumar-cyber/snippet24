(() => {

  const state = {

    stories: [],

    category: "All",

    lang:
      localStorage.getItem("snippet24_lang")
      || "en"

  };


  const $ = selector =>
    document.querySelector(selector);


  const $$ = selector =>
    [...document.querySelectorAll(selector)];



  /* --------------------------------
     LANGUAGE DATA
  -------------------------------- */

  function getTitle(story) {

    return (
      story?.translations?.[state.lang]?.title ||

      story?.[state.lang]?.title ||

      story?.title ||

      ""
    );

  }


  function getSummary(story) {

    return (
      story?.translations?.[state.lang]?.summary ||

      story?.[state.lang]?.summary ||

      story?.summary ||

      ""
    );

  }


  function getPoints(story) {

    return (
      story?.translations?.[state.lang]?.key_points ||

      story?.[state.lang]?.key_points ||

      story?.key_points ||

      []
    );

  }


  function categoryOf(story) {

    return (
      story.category ||

      story.section ||

      "India"
    );

  }


  function sourceOf(story) {

    return (
      story.source_url ||

      story.original_url ||

      story.url ||

      ""
    );

  }


  function imageOf(story) {

    return (
      story.ai_image_url ||

      story.image ||

      story.image_url ||

      story.ai_image ||

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
            cache:"no-store"
          }
        );


      if(response.ok) {

        data =
          await response.json();

      }

    }

    catch(error) {

      console.log(
        "API unavailable"
      );

    }



    /*
      If backend is unavailable,
      use articles.json.
    */

    if(!data) {

      try {

        const response =
          await fetch(
            "./articles.json",
            {
              cache:"no-store"
            }
          );


        if(response.ok) {

          data =
            await response.json();

        }

      }

      catch(error) {

        console.log(
          "articles.json unavailable"
        );

      }

    }



    /*
      Support several JSON structures.
    */

    if(Array.isArray(data)) {

      state.stories = data;

    }

    else if(
      Array.isArray(data?.stories)
    ) {

      state.stories =
        data.stories;

    }

    else if(
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
          For languages other than English,
          only show stories that actually
          have that translation.
        */

        const hasTranslation =
          state.lang === "en"
          ||
          !!(
            story.translations?.[
              state.lang
            ]

            ||

            story[
              state.lang
            ]
          );


        const category =
          categoryOf(story);


        return (

          hasTranslation

          &&

          (
            state.category === "All"

            ||

            category ===
            state.category
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


    if(element) {

      element.textContent =
        text;

    }

  }



  /* --------------------------------
     SECURITY / HTML ESCAPE
  -------------------------------- */

  function escapeHtml(value = "") {

    return String(value)

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



  /* --------------------------------
     STORY CARD
  -------------------------------- */

  function storyCard(story) {

    const title =
      getTitle(story);


    const summary =
      getSummary(story);


    const points =
      getPoints(story);


    const source =
      sourceOf(story);


    const image =
      imageOf(story);


    const signal =
      story.signal

      ||

      (
        story.breaking
          ? "BREAKING"
          : "IMPORTANT"
      );



    let imageHTML;


    if(image) {

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



    const pointsHTML =
      points.length

      ?

      `

      <ul class="key-points">

        ${points
          .slice(0,3)
          .map(
            point =>
              `<li>
                ${escapeHtml(point)}
              </li>`
          )
          .join("")
        }

      </ul>

      `

      :

      "";



    const summaryHTML =
      summary

      ?

      `

      <div class="why">

        <b>
          WHY IT MATTERS
        </b>

        <br>

        ${escapeHtml(summary)}

      </div>

      `

      :

      "";



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
              story.published_at

              ?

              " • " +

              escapeHtml(
                new Date(
                  story.published_at
                ).toLocaleString()
              )

              :

              ""
            }

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


    if(stories.length) {

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

    const items =
      stories.slice(0,12);


    const ticker =
      $("#tickerTrack");


    if(!items.length) {

      ticker.innerHTML = `

        <span>

          Live Wire will appear
          when stories are published.

        </span>

      `;

      return;

    }



    /*
      Duplicate the stories so the
      ticker can move continuously.
    */

    const combined =
      [...items,...items];


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
     ACTIVE BUTTONS
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


    $("#languageSelect").value =
      state.lang;

  }



  /* --------------------------------
     CATEGORY
  -------------------------------- */

  function setCategory(category) {

    state.category =
      category;


    $("#signal")
      .scrollIntoView({

        behavior:"smooth",

        block:"start"

      });


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



  /* --------------------------------
     MORE
  -------------------------------- */

  $("#moreBtn")
    .addEventListener(
      "click",

      () => {

        $("#moreMenu")
          .classList.toggle(
            "show"
          );

      }
    );



  /* --------------------------------
     VIEW ALL
  -------------------------------- */

  $("#viewAllBtn")
    .addEventListener(
      "click",

      () => {

        setCategory("All");

      }
    );



  /* --------------------------------
     REFRESH
  -------------------------------- */

  $("#refreshBtn")
    .addEventListener(
      "click",

      loadStories

    );



  /* --------------------------------
     CATCH ME UP
  -------------------------------- */

  $("#catchupBtn")
    .addEventListener(
      "click",

      () => {

        state.category =
          "All";


        $("#signal")
          .scrollIntoView({

            behavior:"smooth",

            block:"start"

          });


        render();

      }
    );



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

            $("#signal")
              .scrollIntoView({

                behavior:"smooth",

                block:"start"

              });

          }
        );

      }
    );



  /* --------------------------------
     SEARCH
  -------------------------------- */

  $("#searchBtn")
    .addEventListener(
      "click",

      () => {

        $("#searchPanel")
          .classList.add("show");


        $("#searchInput")
          .focus();

      }
    );



  $("#closeSearch")
    .addEventListener(
      "click",

      () => {

        $("#searchPanel")
          .classList.remove(
            "show"
          );

      }
    );



  $("#searchPanel")
    .addEventListener(
      "click",

      event => {

        if(
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



  $("#searchInput")
    .addEventListener(
      "input",

      event => {

        const query =
          event.target.value
            .trim()
            .toLowerCase();


        const results =
          state.stories

            .filter(
              story =>
                getTitle(story)
                  .toLowerCase()
                  .includes(query)
            )

            .slice(0,8);


        $("#searchResults")
          .innerHTML =

          query

          ?

          results
            .map(
              story => {

                const source =
                  sourceOf(story);


                if(source) {

                  return `

                    <a

                      class="search-result"

                      href="${escapeHtml(source)}"

                      target="_blank"

                      rel="noopener"

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

          :

          "";

      }
    );



  /* --------------------------------
     START
  -------------------------------- */

  loadStories();

})();