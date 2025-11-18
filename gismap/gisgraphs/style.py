from string import Template


# language=css
default_style = Template("""

                         #box-$uid {
                             position: relative;
                             width: 100% !important;
                             height: 80vh !important;
                             max-width: 100vw !important;
                             max-height: 80vh !important;
                             min-height: 80vh;
                             color: #111;
                         }

                         #vis-$uid {
                             height: 100%; /* Make the inner div fill the parent */
                             width: 100%; /* Make the inner div fill the parent */
                             box-sizing: border-box;
                             border: 1px solid #444;
                         }

                         html[data-theme="dark"] #vis-$uid {
                             background-color: var(--pst-color-background, #14181e);
                         }

                         .modal {
                             display: none;
                             position: fixed;
                             z-index: 1000;
                             left: 0;
                             top: 0;
                             width: 100%;
                             height: 100%;
                             overflow: auto;
                             background-color: rgba(10, 10, 10, 0.85);
                         }

                         .modal-content {
                             background-color: #f4f4f7;
                             color: #222235;
                             margin: 10% auto;
                             padding: 24px;
                             border: 1px solid #888;
                             width: 50%;
                             border-radius: 8px;
                             box-shadow: 0 5px 15px rgba(0, 0, 0, .6);
                         }
                         .modal a {color: #2958d7;}
                         .modal a:visited {color: #8435a8;}

                         .close {
                             color: #777;
                             float: right;
                             font-size: 28px;
                             font-weight: bold;
                             cursor: pointer;
                         }

                         .close:hover, .close:focus {
                             color: #aaa;
                             text-decoration: none;
                             cursor: pointer;
                         }

                         .watermark {
                             position: absolute;
                             text-decoration: none;
                             color: #888;
                             font-size: min(2vw, 10px);
                             z-index: 10;
                         }

                         .gislink {
                             left: 10px;
                             bottom: 10px;
                             pointer-events: auto;
                         }

                         .button {
                             background: none;
                             border: none;
                             padding: 0;
                             margin: 0;
                             cursor: pointer;
                         }

                         .redraw {
                             left: 10px;
                             top: 10px;
                         }

                         .fullscreen {
                             bottom: 10px;
                             right: 10px;
                         }

                         .legend {
                             display: inline-block;
                             padding: 10px 16px;
                             border-radius: 8px;
                             box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.10);
                             border: 1px solid var(--legend-border, #bbb);
                             background: var(--jp-layout-color1, #f5f5fa);
                             background-color: var(--legend-bg, rgba(240, 240, 245, 0.95));
                             position: absolute;
                             top: 12px;
                             right: 12px;
                             z-index: 20;
                         }

                         .legend-entry {
                             display: flex;
                             margin-right: 10px;
                             align-items: center;
                             cursor: pointer;
                         }
                         """)
