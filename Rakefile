# Rakefile
require 'mini_magick'
require 'logger'
require 'openai'
require 'fileutils'
require 'dotenv/load'  # Lädt .env Datei automatisch
require_relative 'lib/location_generator'

namespace :locations do
  desc 'Generate location entries from text file using OpenAI'
  task :generate, [:input_file] do |t, args|
    logger = Logger.new(STDOUT)
    logger.info("Starting location generation task")

    # Prüfe ob Input-Datei angegeben wurde
    input_file = args[:input_file] || 'orte_heuweiler.txt'
    
    # LocationGenerator initialisieren
    generator = LocationGenerator.new(logger)
    generator.ensure_locations_directory

    begin
      # Orte aus Datei laden
      places = generator.load_places_from_file(input_file)
      logger.info("Processing #{places.length} places...")

      places.each_with_index do |place, index|
        next if place.empty?

        # Prüfen ob Datei bereits existiert
        if generator.file_exists?(place)
          logger.info("Skipping #{place} - file already exists")
          next
        end

        logger.info("Processing #{index + 1}/#{places.length}: #{place}")

        # Process single location ohne Temperature-Parameter
        result = generator.process_single_location(place)
        
        if result[:success]
          logger.info("Created: #{File.basename(result[:file])}")
          # Kurze Pause um API Rate Limits zu respektieren
          sleep(1)
        else
          logger.error("Failed to process #{place}: #{result[:error]}")
        end
      end

    rescue => e
      logger.error("Error: #{e.message}")
      exit 1
    end

    logger.info("Finished location generation task")
  end

  desc 'Test generation for a single location'
  task :test, [:place_name] do |t, args|
    logger = Logger.new(STDOUT)
    
    unless args[:place_name]
      logger.error("Please provide a place name: rake locations:test['Altvogtshof']")
      exit 1
    end

    place_name = args[:place_name].strip
    logger.info("Testing location generation for: #{place_name}")

    # LocationGenerator initialisieren
    generator = LocationGenerator.new(logger)
    generator.ensure_locations_directory

    # Dateiname generieren und anzeigen
    filename = generator.generate_filename(place_name)
    logger.info("Generated filename: #{filename}")
    logger.info("Test file will be saved as: test_#{filename}")

    # OpenAI Prompt für den Ort anzeigen
    prompt = generator.create_location_prompt(place_name)
    
    logger.info("Generated prompt:")
    logger.info("-" * 50)
    puts prompt
    logger.info("-" * 50)

    begin
      logger.info("Sending request to OpenAI...")
      
      # Verwendet test_only: true um nur die Test-Datei zu erstellen
      result = generator.process_single_location(place_name, test_only: true)
      
      if result[:success]
        logger.info("✅ SUCCESS! Generated content:")
        logger.info("=" * 60)
        puts result[:content].strip
        logger.info("=" * 60)
        logger.info("📁 Saved to: #{result[:file]}")
      else
        logger.error("❌ Error: #{result[:error]}")
      end

    rescue => e
      logger.error("❌ Error processing #{place_name}: #{e.message}")
      logger.error("Full error: #{e.inspect}")
    end

    logger.info("Test completed for: #{place_name}")
  end

  desc 'Show available places from orte_heuweiler.txt'
  task :list do |t|
    input_file = 'orte_heuweiler.txt'
    generator = LocationGenerator.new

    begin
      places = generator.load_places_from_file(input_file)
      
      puts "📍 Available places in #{input_file}:"
      puts "=" * 50
      
      places.each_with_index do |place, index|
        next if place.empty?
        
        status = generator.file_exists?(place) ? "✅" : "⏳"
        puts "#{sprintf('%3d', index + 1)}: #{status} #{place}"
      end
      
      puts "=" * 50
      puts "Total: #{places.length} places"
      puts "✅ = Already generated"
      puts "⏳ = Not yet generated"
      puts ""
      puts "Usage examples:"
      puts "  rake locations:test['Altvogtshof']"
      puts "  rake locations:test['Hotel & Restaurant Laube']"

    rescue => e
      puts "❌ Error: #{e.message}"
      exit 1
    end
  end
end

namespace :images do
  desc 'Remove all 800px images'
  task :remove_800px do
    logger = Logger.new(STDOUT)
    logger.info("Starting image removal task")

    Dir.glob('assets/images/**/*_800px.*') do |image_path|
      if File.exist?(image_path)
        File.delete(image_path)
        logger.info("Removed image: #{image_path}")
      end
    end

    logger.info("Finished image removal task")
  end

  desc 'Optimize and resize images'
  task :optimize do
    logger = Logger.new(STDOUT)
    logger.info("Starting image optimization task")

    Dir.glob('assets/images/**/*.{jpg}') do |image_path|
      # Skip images in the '.noresize' folder
      next if image_path.include?('/noresize/')

      image = MiniMagick::Image.open(image_path)

      # Resize only if width or height is greater than 800px
      if image.width > 800 || image.height > 800
        image.resize '800x800'
        # Optimize the image
        image.strip
        # Write the changes to the original image
        image.write image_path
        logger.info("Resized, optimized and wrote image to #{image_path}")
      end
    end

    logger.info("Finished image optimization task")
  end

  desc 'Find all PNG images and output their file size and resolution'
  task :info do
    logger = Logger.new(STDOUT)
    logger.info("Starting image info task")

    Dir.glob('assets/images/**/*.{png}') do |image_path|
      image = MiniMagick::Image.open(image_path)

      # Get the file size
      file_size = File.size(image_path)

      # Get the resolution
      resolution = "#{image.width}x#{image.height}"

      logger.info("Image: #{image_path}, Size: #{file_size} bytes, Resolution: #{resolution}")
    end

    logger.info("Finished image info task")
  end

  desc 'Rename .jpeg files to .jpg'
  task :rename do
    directory = 'assets/images'

    Dir.glob("#{directory}/**/*").each do |file|
      if File.file?(file) && File.extname(file) == '.jpeg'
        new_file = file.sub(/\.jpeg$/, '.jpg')
        FileUtils.mv(file, new_file)
        logger.info "Renamed #{file} to #{new_file}"
      end
    end
  end

  desc 'Convert HEIC files to JPG and optimize'
  task :convert_heic_to_jpg do
    logger = Logger.new(STDOUT)
    logger.info("Starting HEIC to JPG conversion task")

    Dir.glob('assets/images/**/*.{HEIC}') do |image_path|
      image = MiniMagick::Image.open(image_path)
      new_image_path = image_path.sub(/\.HEIC$/, '.jpg').downcase
      image.format 'jpg'
      image.write new_image_path
      logger.info("Converted #{image_path} to #{new_image_path}")

      if image.width > 800 || image.height > 800
        image.resize '800x800'
        image.strip
        image.write new_image_path
        logger.info("Resized, optimized and wrote image to #{new_image_path}")
      end
    end

    logger.info("Finished HEIC to JPG conversion task")
  end
  
end