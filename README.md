
# DjangoCMS Content Transfer

Usefull to transfer Page-, PageContent-, Alias-, Placeholder-Objects from one CMS System to another. 

## Plugins supported:

- all djangocms plus plugins and descendants
- djangocms-alias plugins
- djangocms-text plugins

## Usage

### Page Export to an other instance

1. Go to Django Admin > Transfer
2. Create new PageExport model
3. Select a Page to export
4. Save PageExport model
5. Copy generated json data section and switch to other system for `Page Import`

Note: always the latest PageContent obj is used to export a Page

### Page Import from an other instance

1. Go to Django Admin > Transfer
2. Create new PageImport model
3. paste in copied json
4. Select parent page or leave blank to import into top level.
5. Save Model
6. Click Import Button

### Alias Export to an other instance

See Page Export, but with AliasExport model

### Alias Import from an other instance

See Page Import, but with AliasImport model

### Placeholder Export to an other instance

1. Go to any CMS Page and select `Copy all` in a Placeholder menu to copy all plugins to clipboard.
2. Go to Django Admin > Transfer
3. Create new PlaceholderExport model
4. Save PlaceholderExport model
5. Copy generated json data section and switch to other system for `Placeholder Import`

### Placeholder Import from an other instance

1. Go to Django Admin > Transfer
2. Create new PlaceholderImport model
3. paste in copied json
4. Save Model
5. Click Copy to Clipboard Button
6. Go to any Page and select Placeholder > Paste menu

```
ExportItem Model:

type: Page, Placeholder, Alias
data: {
  page_id
  reverse_id
  languages
  pages: [],
  page_contents [              # home.get_content_obj(), home.get_child_pages()
    {
      language: de
      title
      page_title
      menu_title
      meta_description
      in_navigation
      template
      placeholders: [
        {                          # hc_header.get_plugins().filter(id__in=hc_header.get_plugin_tree_order('de'))
          slot: header,
          extra_context: {},
          plugins: [
            {
              plugin_type: GridContainerPlugin,             # plugin.get_children()
              config: {},
              children: [
                {
                  plugin_type: AliasPlugin,
                  config: { bei bildern: sha1 mit, bei internal links: absolute_url },
                  children: [

                  ]
                },
              ]
            },
            {}
          ]
        }
      ]
    },
    {
      language: en
      title
      page_title
      menu_title
      meta_description
      in_navigation
      template
    }
  ]
}
```