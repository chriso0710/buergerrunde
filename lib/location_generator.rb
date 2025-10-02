# lib/location_generator.rb
require 'openai'
require 'fileutils'
require 'logger'

class LocationGenerator
  # Konstanten für OpenAI API
  DEFAULT_MODEL = "gpt-5-mini"
  
  # Faraday Timeout-Konstanten (in Sekunden)
  REQUEST_TIMEOUT = 180  # Timeout für einzelne HTTP-Requests
  OPEN_TIMEOUT = 30     # Timeout für das Öffnen der Verbindung

  attr_reader :logger, :client

  def initialize(logger = nil)
    @logger = logger || Logger.new(STDOUT)
    @client = initialize_openai_client
  end

  def ensure_locations_directory
    locations_dir = '_locations'
    FileUtils.mkdir_p(locations_dir) unless Dir.exist?(locations_dir)
  end

  def generate_filename(place_name)
    place_name.downcase
              .gsub(/[äöü]/, 'ä' => 'ae', 'ö' => 'oe', 'ü' => 'ue')
              .gsub(/ß/, 'ss')
              .gsub(/[^a-z0-9\s-]/, '')
              .gsub(/\s+/, '-')
              .gsub(/-+/, '-') + '.md'
  end

  def generate_location_content(place_name)
    prompt = create_location_prompt(place_name)

    logger.info("🔄 Sending OpenAI request for: #{place_name}")
    logger.info("📊 Request parameters: model=#{DEFAULT_MODEL}")

    response = client.responses.create(
      parameters: {
        model: DEFAULT_MODEL,
        input: prompt,
        tools: [
            { type: "web_search" },
        ]
      }
    )

    # Parse response basierend auf Model-Typ
    content = parse_response_content(response)
    
    # Entferne Markdown Code Block Wrapper falls vorhanden
    if content
      content = clean_markdown_wrapper(content)
    end
    
    # Zeige Token-Usage falls verfügbar
    show_token_usage(response)
    
    content
  end

  def create_location_prompt(place_name)
    <<~PROMPT
**Aufgabe:**
Erstelle einen Markdown-Eintrag für den Ort „#{place_name}" in Heuweiler, Baden-Württemberg, Deutschland.

**Kontext:**
Heuweiler ist eine kleine Gemeinde im Breisgau-Hochschwarzwald zwischen Freiburg und Emmendingen mit ca. 1000 Einwohnern.

**Rechercheanforderungen:**

* Suche im Internet nach dem Ort.
* Ergänze ggf. relevante soziale Medien oder Verzeichniseinträge.
* Suche im Internet ein Bild des Ortes in geeigneter Auflösung (mind. 300x300 px). Wichtig ist, dass es ein Direktlink zu einem Bild ist. Falls du kein passendes findest, lasse das Feld leer.
* Suche im Internet die offizielle Website des Ortes. Falls du keine findest, lasse das Feld leer.
* Versuche bestmöglich, die genauen Geo Koordinaten des Ortes zu finden. Gib keine fiktiven Koordinaten an. Falls du keine genauen Koordinaten findest, lasse die Felder leer.

**Ausgabeformat:**
Antworte ausschließlich in Markdown mit:

1. **YAML Front Matter** mit folgenden Feldern:

   * `title`: Vollständiger Name des Ortes
   * `latitude`: realistische Latitude (Format: 48.xxxx)
   * `longitude`: realistische Longitude (Format: 7.xxxx)
   * `category`: genau **eine** Kategorie aus dieser Liste wählen:
     * Bauernhöfe
     * Öffentliche Gebäude
     * Religiöse Stätten
     * Veranstaltungsorte
     * Geschäfte & Gastronomie
     * Handwerk & Gewerbe
     * Wohngebiete
     * Straßen & Wege
     * Naturdenkmäler
     * Historische Gebäude
     * Infrastruktur
   * `description`: kurze Beschreibung in einem Satz
   * `address`: vollständige Adresse, sonst „Heuweiler, Baden-Württemberg"
   * `website`: Website-URL mit des Ortes, mit `https://`
   * `image`: URL zu einem Bild des Ortes
   * `generated_by`: "#{DEFAULT_MODEL}"
   * `generated_at`: "#{Time.now.strftime('%Y-%m-%d %H:%M:%S %z')}"

2. **Markdown-Inhalt** mit:

   * 2–3 Absätze Beschreibung des Ortes
   * Besonderheiten oder interessante Fakten
   * Bedeutung/Verwendungszweck für Heuweiler
   * ggf. Geschichte, Ausstattung, Veranstaltungen
   * wichtige Kontaktinfos (Telefon, E-Mail)
   * Öffnungszeiten, falls relevant

**Regeln:**

* Verwende **genau eine** Kategorie.
* Verwende Markdown für Überschriften ab Ebene 4 (#### Überschrift).
* Prüfe ob die URL der Website und des Bildes wirklich existiert. Wenn nicht, dann suche weiter.
* Antwort nur als Markdown-Dokument, ohne zusätzliche Erklärungen oder Kommentare. 
* Gib keine Erklärungen oder Kommentare im Markdown ab. Wenn du Kommentare hast, schreibe sie in den Frontmatter-Header als `notes`.
    PROMPT
  end

  def file_exists?(place_name)
    filename = generate_filename(place_name)
    file_path = File.join('_locations', filename)
    File.exist?(file_path)
  end

  def save_content(place_name, content, prefix: nil)
    filename = generate_filename(place_name)
    filename = "#{prefix}_#{filename}" if prefix
    file_path = File.join('_locations', filename)
    
    File.write(file_path, content.strip)
    file_path
  end

  def process_single_location(place_name, save_test_file: false, test_only: false)
    logger.info("Processing: #{place_name}")

    begin
      content = generate_location_content(place_name)
      
      if content && !content.strip.empty?
        files_created = []
        
        # Test-only Modus: nur Test-Datei erstellen
        if test_only
          test_file = save_content(place_name, content, prefix: 'test')
          logger.info("Test file created: #{test_file}")
          files_created << test_file
          return { success: true, content: content, file: test_file, files: files_created }
        end
        
        # Normale Datei speichern (außer im test_only Modus)
        main_file = save_content(place_name, content)
        logger.info("Created: #{main_file}")
        files_created << main_file
        
        # Optional: zusätzliche Test-Datei speichern
        if save_test_file
          test_file = save_content(place_name, content, prefix: 'test')
          logger.info("Test file created: #{test_file}")
          files_created << test_file
        end
        
        return { success: true, content: content, file: main_file, files: files_created }
      else
        logger.error("Empty response for #{place_name}")
        return { success: false, error: "Empty response" }
      end

    rescue => e
      logger.error("Error processing #{place_name}: #{e.message}")
      return { success: false, error: e.message }
    end
  end

  def load_places_from_file(filename)
    unless File.exist?(filename)
      raise "Input file #{filename} not found!"
    end

    File.readlines(filename, chomp: true).reject(&:empty?).map(&:strip)
  end

  private

  def initialize_openai_client
    unless ENV['OPENAI_API_KEY']
      logger.error("OPENAI_API_KEY environment variable not set!")
      exit 1
    end
    
    # OpenAI Client mit Faraday Logging und Timeout-Konfiguration
    client = OpenAI::Client.new(
      access_token: ENV['OPENAI_API_KEY'],
      log_errors: true  # Aktiviert Error-Logging
    ) do |faraday|
      # Timeout-Konfiguration
      faraday.options.timeout = REQUEST_TIMEOUT      # Request timeout
      faraday.options.open_timeout = OPEN_TIMEOUT    # Connection timeout
      
      # Request/Response Logger - zeigt Headers, Body, etc.
      faraday.response :logger, logger, { headers: true, bodies: true, errors: true }
    end
    
    logger.info("🔑 OpenAI Client initialized with detailed logging")
    logger.info("⏱️ Timeouts configured: request=#{REQUEST_TIMEOUT}s, open=#{OPEN_TIMEOUT}s")
    client
  end

  def clean_markdown_wrapper(content)
    return content unless content
    
    # Entferne führende und nachfolgende Whitespace
    cleaned = content.strip
    
    # Entferne ```markdown am Anfang
    if cleaned.start_with?('```markdown')
      cleaned = cleaned.sub(/^```markdown\s*\n?/, '')
    elsif cleaned.start_with?('```')
      cleaned = cleaned.sub(/^```\s*\n?/, '')
    end
    
    # Entferne ``` am Ende
    if cleaned.end_with?('```')
      cleaned = cleaned.sub(/\n?\s*```$/, '')
    end
    
    # Entferne wieder führende/nachfolgende Whitespace nach der Bereinigung
    cleaned.strip
  end

  def parse_response_content(response)
    # Für Reasoning Models (gpt-5-mini) - neue Struktur
    if response.dig("output")
      # Finde den message output im output array
      message_output = response["output"].find { |output| output["type"] == "message" }
      if message_output && message_output.dig("content")
        # Content ist ein Array mit text objects
        text_content = message_output["content"].find { |c| c["type"] == "output_text" }
        return text_content["text"] if text_content
      end
    end
    
    # Fallback für normale Chat Completion API Struktur
    response.dig("choices", 0, "message", "content")
  end

  def show_token_usage(response)
    usage = response.dig("usage")
    return unless usage

    logger.info("📊 Token Usage:")
    logger.info("   Input tokens: #{usage['input_tokens']}")
    logger.info("   Output tokens: #{usage['output_tokens']}")
    logger.info("   Total tokens: #{usage['total_tokens']}")
    
    # Spezielle Informationen für Reasoning Models
    if usage.dig("output_tokens_details", "reasoning_tokens")
      logger.info("   Reasoning tokens: #{usage['output_tokens_details']['reasoning_tokens']}")
    end
    
    if usage.dig("input_tokens_details", "cached_tokens")
      logger.info("   Cached tokens: #{usage['input_tokens_details']['cached_tokens']}")
    end
  end
end