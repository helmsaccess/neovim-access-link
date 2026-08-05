-- Keep Markdown links useful in the repository while pointing the standalone
-- German quick guide at the corresponding generated handbook sections.
local targets = {
  ["README.md"] = "neovim-access-link-handbook-de.html",
  ["example-configuration.md"] = "neovim-access-link-handbook-de.html#docs__de__manual__example-configurationmd__kleine-python-konfiguration-mit-lazy-und-oil",
}

function Link(link)
  local path = link.target:match("^([^#]+)") or link.target
  local replacement = targets[path]
  if replacement then
    link.target = replacement
    return link
  end
end
