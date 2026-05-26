# FFML

FFML is a simple markup language combining aspects of BBCode and Markdown, designed for writing fanfics in a format that's flexible but that remains 'plain'. 

* Readable formatting (`*italics*`, `**bold**`, `_underline_`, `~strikethrough~`, `$small caps$`)
* Styled divs and spans (`[.center; Centered div]`, `<.red; Red span>`)
* Comments (`{ Annotate your writing however you want! }`)
* Escaped text (`` You're a `****`. ``)
* Multiple types of breaks (scene breaks, section breaks, line breaks)
* Marking of the first paragraph after the start of the document, after a section, or after a block.
* Support for European em-dash delimited dialogue (`= I hate you = she said hatefully. = I despise you.`)

## Usage

```
usage: render.py [-h] [--output OUTPUT] [--template TEMPLATE] [--config CONFIG] [source]

Render a markup file to HTML

positional arguments:
  source                input file; reads from stdin if omitted

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        output file; writes to stdout if omitted
  --template TEMPLATE, -t TEMPLATE
                        HTML template file with {{content}} placeholder
  --config CONFIG, -c CONFIG
                        JSON config file
```

The generated HTML relies on CSS styling to display correctly. The stylesheet `style.css` is provided as an example.

## Config

The configuration file allows the user to customise aspects of the rendering. `config.json` in this repo is provided as an example and doesn't represent the defaults.

```json
{
  "breaks": {
    "=": {
      "tag": "p",
      "class": "hard-break",
      "text": "✱ ✱ ✱"
    },
    "-": {
      "tag": "p",
      "class": "soft-break"
    },
    ">": {
      "tag": "br",
      "class": "line-break"
    },
    "<": {
      
    }
  },
  "small_caps_class": "small-caps"
}

```


---

Input-output example pairs are provided in the `examples` directory.
