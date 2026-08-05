-- Keep Markdown links useful in the repository while pointing the standalone
-- English quick guide at the corresponding generated handbook sections.
local targets = {
  ["README.md"] = "neovim-access-link-handbook-en.html",
  ["example-configuration.md"] = "neovim-access-link-handbook-en.html#docs__en__manual__example-configurationmd__small-python-configuration-with-lazy-and-oil",
}

function Link(link)
  local path = link.target:match("^([^#]+)") or link.target
  local replacement = targets[path]
  if replacement then
    link.target = replacement
    return link
  end
end
