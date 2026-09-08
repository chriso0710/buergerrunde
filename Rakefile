# Rakefile
require 'mini_magick'
require 'logger'
require 'fileutils'
require 'dotenv/load'  # Lädt .env Datei automatisch

namespace :locations do
  desc 'Geocode all location files using Nominatim API and update coordinates'
  task :geocode do
    require 'net/http'
    require 'uri'
    require 'json'
    require 'yaml'
    
    logger = Logger.new(STDOUT)
    logger.info("Starting geocoding task for all location files")

    locations_dir = '_locations'
    unless Dir.exist?(locations_dir)
      logger.error("Locations directory not found: #{locations_dir}")
      exit 1
    end

    # Alle .md Dateien im _locations Verzeichnis
    location_files = Dir.glob("#{locations_dir}/*.md")
    
    if location_files.empty?
      logger.info("No location files found in #{locations_dir}")
      exit 0
    end

    logger.info("Found #{location_files.length} location files to process")
    
    success_count = 0
    error_count = 0
    
    location_files.each_with_index do |file_path, index|
      logger.info("Processing #{index + 1}/#{location_files.length}: #{File.basename(file_path)}")
      
      begin
        # Datei lesen
        content = File.read(file_path)
        
        # YAML Front Matter extrahieren
        if content =~ /\A---\s*\n(.*?)\n---\s*\n(.*)/m
          yaml_content = $1
          markdown_content = $2
          
          # YAML parsen
          front_matter = YAML.load(yaml_content)
          
          # Prüfen ob Adresse vorhanden ist
          unless front_matter['address']
            logger.warn("No address found in #{File.basename(file_path)}, skipping")
            next
          end
          
          address = front_matter['address']
          logger.info("  Address: #{address}")
          
          # Nominatim API aufrufen
          encoded_address = URI.encode_www_form_component(address)
          api_url = "https://nominatim.openstreetmap.org/search?q=#{encoded_address}&format=json&limit=1&addressdetails=1"
          
          uri = URI(api_url)
          http = Net::HTTP.new(uri.host, uri.port)
          http.use_ssl = true
          
          # User-Agent setzen (erforderlich für Nominatim)
          request = Net::HTTP::Get.new(uri)
          request['User-Agent'] = 'Buergerrunde Jekyll Site (https://buergerrunde.heuweiler.net)'
          
          response = http.request(request)
          
          if response.code == '200'
            results = JSON.parse(response.body)
            
            if results.empty?
              logger.warn("  No geocoding results found for address")
              error_count += 1
              next
            end
            
            result = results.first
            new_lat = result['lat'].to_f.round(6)
            new_lng = result['lon'].to_f.round(6)
            
            old_lat = front_matter['latitude']
            old_lng = front_matter['longitude']
            
            logger.info("  Old coordinates: #{old_lat}, #{old_lng}")
            logger.info("  New coordinates: #{new_lat}, #{new_lng}")
            
            # Koordinaten aktualisieren
            front_matter['latitude'] = new_lat
            front_matter['longitude'] = new_lng
            
            # Datei neu schreiben
            new_content = "---\n#{front_matter.to_yaml.sub(/^---\n/, '')}---\n#{markdown_content}"
            File.write(file_path, new_content)
            
            logger.info("  ✅ Updated coordinates in #{File.basename(file_path)}")
            success_count += 1
            
          else
            logger.error("  API request failed with code #{response.code}")
            error_count += 1
          end
          
        else
          logger.warn("No valid YAML front matter found in #{File.basename(file_path)}")
          error_count += 1
        end
        
      rescue => e
        logger.error("  Error processing #{File.basename(file_path)}: #{e.message}")
        error_count += 1
      end
      
      # Pause zwischen API-Aufrufen (Nominatim Rate Limit respektieren)
      sleep(1) unless index == location_files.length - 1
    end
    
    logger.info("Geocoding completed!")
    logger.info("✅ Successfully processed: #{success_count} files")
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