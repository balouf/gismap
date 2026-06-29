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
                             background-color: var(--pst-color-background, var(--jp-layout-color0, white));
                         }

                         #box-$uid:fullscreen {
                             height: 100vh !important;
                             max-height: 100vh !important;
                             min-height: 100vh;
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

                         /* Forced theme (menu toggle). 'auto' adds no class and
                            follows the host; gm-light/gm-dark redefine the CSS
                            vars on the box and the (reparented) modal. */
                         #box-$uid.gm-light, #modal-$uid.gm-light {
                             --pst-color-background: #ffffff;
                             --pst-color-on-background: #ffffff;
                             --pst-color-text-base: #1b1b2b;
                             --pst-color-border: #c2c2cc;
                             --pst-color-surface: #f0f0f4;
                             --pst-color-link: #2958d7;
                             --pst-color-link-hover: #8435a8;
                             --pst-color-primary: #3b65b2;
                             --legend-bg: rgba(244, 244, 248, 0.96);
                             --legend-border: #c2c2cc;
                             --legend-text: #1b1b2b;
                         }

                         #box-$uid.gm-dark, #modal-$uid.gm-dark {
                             --pst-color-background: #14181e;
                             --pst-color-on-background: #1f242c;
                             --pst-color-text-base: #e7e7ec;
                             --pst-color-border: #4d535d;
                             --pst-color-surface: #2a2f38;
                             --pst-color-link: #79a6ff;
                             --pst-color-link-hover: #c69bf0;
                             --pst-color-primary: #5b86d6;
                             --legend-bg: rgba(31, 36, 44, 0.96);
                             --legend-border: #4d535d;
                             --legend-text: #e7e7ec;
                         }

                         #box-$uid.gm-light { background-color: #ffffff; }
                         #box-$uid.gm-dark { background-color: #14181e; }
                         #box-$uid.gm-light #vis-$uid { background-color: #ffffff; }
                         #box-$uid.gm-dark #vis-$uid { background-color: #14181e; }

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
                             background-color: var(--pst-color-on-background, var(--jp-layout-color0, #f4f4f7));
                             color: var(--pst-color-text-base, var(--jp-content-font-color1, #222235));
                             margin: 10% auto;
                             padding: 24px;
                             border: 1px solid var(--pst-color-border, #888);
                             width: 50%;
                             border-radius: 8px;
                             box-shadow: 0 5px 15px rgba(0, 0, 0, .6);
                         }
                         .modal a {color: var(--pst-color-link, var(--jp-content-link-color, #2958d7));}
                         .modal a:visited {color: var(--pst-color-link-hover, #8435a8);}

                         .modal-header {
                             display: flex;
                             align-items: center;
                             gap: 16px;
                             margin-bottom: 0.6em;
                         }

                         .modal-title {
                             flex: 1 1 auto;
                             min-width: 0;
                         }

                         .modal-actions {
                             flex: 0 0 auto;
                         }

                         .modal-actions a.dl-all-bib {
                             display: inline-block;
                             font-size: 0.9em;
                             text-decoration: none;
                             padding: 0.15em 0.6em;
                             border: 1px solid var(--pst-color-border, #bbb);
                             border-radius: 4px;
                             white-space: nowrap;
                         }

                         .close {
                             flex: 0 0 auto;
                             color: #777;
                             font-size: 28px;
                             font-weight: bold;
                             line-height: 1;
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

                         .menu-wrap {
                             position: absolute;
                             left: 10px;
                             top: 10px;
                             z-index: 30;
                         }

                         .menu-wrap .menu {
                             position: static;
                             color: var(--pst-color-text-base, var(--jp-content-font-color1, #888));
                             padding: 4px;
                             border-radius: 3px;
                             display: inline-flex;
                             align-items: center;
                             justify-content: center;
                             pointer-events: auto;
                         }

                         .menu-wrap .menu:hover, .menu-wrap .menu:focus {
                             background: var(--pst-color-surface, var(--jp-layout-color2, rgba(0, 0, 0, 0.08)));
                         }

                         .menu-list {
                             list-style: none;
                             list-style-type: none;
                             margin: 4px 0 0 0;
                             padding: 4px 0;
                             min-width: 200px;
                             background: var(--pst-color-on-background, var(--jp-layout-color0, #fff));
                             color: var(--pst-color-text-base, var(--jp-content-font-color1, #222235));
                             border: 1px solid var(--pst-color-border, #bbb);
                             border-radius: 6px;
                             box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                             font-size: 13px;
                             line-height: 1.3;
                         }

                         .menu-list li {
                             list-style: none;
                             list-style-type: none;
                             margin: 0;
                             padding: 0;
                             display: block;
                         }

                         .menu-list[hidden] { display: none; }

                         .menu-list .menu-item {
                             display: flex;
                             align-items: center;
                             justify-content: space-between;
                             gap: 14px;
                             padding: 6px 14px;
                             text-decoration: none;
                             color: inherit;
                             white-space: nowrap;
                         }

                         .menu-list .menu-icon {
                             flex-shrink: 0;
                             opacity: 0.65;
                         }

                         .menu-list .menu-item:hover, .menu-list .menu-item:focus {
                             background: var(--pst-color-surface, var(--jp-layout-color2, rgba(0, 0, 0, 0.06)));
                         }

                         .fullscreen {
                             bottom: 10px;
                             right: 10px;
                             color: var(--pst-color-text-base, var(--jp-content-font-color1, #888));
                             padding: 4px;
                             border-radius: 3px;
                             display: inline-flex;
                             align-items: center;
                             justify-content: center;
                             pointer-events: auto;
                         }

                         .fullscreen:hover, .fullscreen:focus {
                             background: var(--pst-color-surface, var(--jp-layout-color2, rgba(0, 0, 0, 0.08)));
                         }

                         .fs-compress { display: none; }
                         #box-$uid:fullscreen .fs-expand { display: none; }
                         #box-$uid:fullscreen .fs-compress { display: inline; }

                         .legend {
                             display: inline-block;
                             padding: 10px 16px;
                             border-radius: 8px;
                             box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.10);
                             border: 1px solid var(--legend-border, #bbb);
                             color: var(--legend-text, #111);
                             background: var(--jp-layout-color1, #f5f5fa);
                             background-color: var(--legend-bg, rgba(240, 240, 245, 0.95));
                             position: absolute;
                             top: 12px;
                             right: 12px;
                             z-index: 20;
                         }

                         .legend-entry, .comet-entry {
                             display: flex;
                             margin-right: 10px;
                             align-items: center;
                             cursor: pointer;
                         }

                         .time-slider {
                             position: absolute;
                             left: 50%;
                             bottom: 14px;
                             transform: translateX(-50%);
                             z-index: 25;
                             width: min(60%, 360px);
                             padding: 8px 16px 10px;
                             border-radius: 8px;
                             border: 1px solid var(--pst-color-border, #bbb);
                             background: var(--pst-color-on-background, var(--jp-layout-color0, #fff));
                             color: var(--pst-color-text-base, var(--jp-content-font-color1, #222235));
                             box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                             font-size: 12px;
                         }

                         .time-slider-label {
                             text-align: center;
                             margin-bottom: 4px;
                             white-space: nowrap;
                         }

                         .time-slider-track {
                             position: relative;
                             height: 22px;
                         }

                         .time-slider-track::before {
                             content: '';
                             position: absolute;
                             left: 0;
                             right: 0;
                             top: 10px;
                             height: 3px;
                             border-radius: 2px;
                             background: var(--pst-color-border, #bbb);
                         }

                         .time-range {
                             position: absolute;
                             left: 0;
                             top: 0;
                             width: 100%;
                             height: 22px;
                             margin: 0;
                             background: none;
                             pointer-events: none;
                             -webkit-appearance: none;
                             appearance: none;
                         }

                         .time-range::-webkit-slider-thumb {
                             pointer-events: auto;
                             -webkit-appearance: none;
                             appearance: none;
                             width: 14px;
                             height: 14px;
                             margin-top: 4px;
                             border: none;
                             border-radius: 50%;
                             background: var(--pst-color-primary, #3b65b2);
                             cursor: pointer;
                         }

                         .time-range::-moz-range-thumb {
                             pointer-events: auto;
                             width: 14px;
                             height: 14px;
                             border: none;
                             border-radius: 50%;
                             background: var(--pst-color-primary, #3b65b2);
                             cursor: pointer;
                         }

                         .time-range::-moz-range-track {
                             background: transparent;
                         }

                         .empty-graph {
                             position: absolute;
                             left: 50%;
                             top: 50%;
                             transform: translate(-50%, -50%);
                             z-index: 15;
                             padding: 8px 16px;
                             border-radius: 6px;
                             pointer-events: none;
                             font-size: 14px;
                             color: var(--pst-color-text-base, #555);
                             background: var(--pst-color-on-background, rgba(255, 255, 255, 0.85));
                         }

                         .pub a.bib-toggle, .pub a.abs-toggle {
                             font-size: 0.85em;
                             text-decoration: none;
                             padding: 0 0.3em;
                             border: 1px solid var(--pst-color-border, #bbb);
                             border-radius: 3px;
                             margin-left: 0.3em;
                         }

                         .pub pre.bib, .pub pre.abs {
                             position: relative;
                             background: var(--pst-color-surface, var(--jp-layout-color2, #f0f0f4));
                             color: var(--pst-color-text-base, inherit);
                             border: 1px solid var(--pst-color-border, #ccc);
                             border-radius: 4px;
                             padding: 0.6em 0.8em;
                             margin: 0.4em 0;
                             font-size: 0.85em;
                             white-space: pre-wrap;
                             word-break: break-word;
                         }

                         .pub pre.bib .copybtn {
                             position: absolute;
                             top: 4px;
                             right: 4px;
                             padding: 0.1em 0.4em;
                             font-size: 0.75em;
                             background: var(--pst-color-on-background, var(--jp-layout-color0, #fff));
                             color: var(--pst-color-text-base, inherit);
                             border: 1px solid var(--pst-color-border, #aaa);
                             border-radius: 3px;
                             cursor: pointer;
                             opacity: 0;
                             transition: opacity 0.15s;
                         }

                         .pub pre.bib:hover .copybtn,
                         .pub pre.bib .copybtn:focus {
                             opacity: 1;
                         }

                         .pub pre.bib .copybtn.copied {
                             color: #fff;
                             background: #2a9d4a;
                             border-color: #2a9d4a;
                             opacity: 1;
                         }
                         """)
