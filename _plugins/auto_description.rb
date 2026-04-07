require 'nokogiri'

Jekyll::Hooks.register [:pages, :documents], :pre_render do |doc|
  next if doc.data['description'] && !doc.data['description'].to_s.strip.empty?

  # Use excerpt or content as source
  source = doc.data['excerpt']&.to_s || doc.content.to_s
  next if source.strip.empty?

  # Strip HTML tags
  text = Nokogiri::HTML.fragment(source).text
  # Normalize whitespace
  text = text.gsub(/\s+/, ' ').strip
  # Remove markdown heading markers
  text = text.gsub(/^#+\s*/, '')

  next if text.empty?

  # Truncate to 155 chars at word boundary
  if text.length > 155
    text = text[0..154].gsub(/\s\S*$/, '') + '…'
  end

  doc.data['description'] = text
end
