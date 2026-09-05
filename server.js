const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT =
  process.env.PORT || 3000;

const MIME_TYPES = {

  ".html":
    "text/html; charset=utf-8",

  ".css":
    "text/css; charset=utf-8",

  ".js":
    "application/javascript; charset=utf-8",

  ".json":
    "application/json; charset=utf-8",

  ".png":
    "image/png",

  ".jpg":
    "image/jpeg",

  ".jpeg":
    "image/jpeg",

  ".webp":
    "image/webp",

  ".svg":
    "image/svg+xml",

  ".ico":
    "image/x-icon"
};


const server =
  http.createServer(
    (request, response) => {

      let requestPath =
        request.url.split("?")[0];

      if (
        requestPath === "/"
      ) {
        requestPath =
          "/index.html";
      }

      const filePath =
        path.join(
          __dirname,
          decodeURIComponent(
            requestPath
          )
        );

      if (
        !filePath.startsWith(
          __dirname
        )
      ) {

        response.writeHead(
          403
        );

        response.end(
          "Forbidden"
        );

        return;
      }


      fs.readFile(
        filePath,
        (error, data) => {

          if (error) {

            response.writeHead(
              404,
              {
                "Content-Type":
                  "text/plain; charset=utf-8"
              }
            );

            response.end(
              "Not found"
            );

            return;
          }


          const extension =
            path.extname(
              filePath
            ).toLowerCase();


          response.writeHead(
            200,
            {
              "Content-Type":
                MIME_TYPES[extension] ||
                "application/octet-stream",

              "Cache-Control":
                "no-cache"
            }
          );


          response.end(data);
        }
      );
    }
  );


server.listen(
  PORT,
  () => {

    console.log(
      `Snippet24 running at http://localhost:${PORT}`
    );
  }
);