# Rakefile
require 'mini_magick'
require 'logger'

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
end

namespace :images do
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
        logger.info("Resized image to 800x800")
      end

      # Optimize the image
      image.strip

      # Write the changes to the original image
      image.write image_path

      logger.info("Optimized and wrote image to #{image_path}")
    end

    logger.info("Finished image optimization task")
  end
end

namespace :images do
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
end

namespace :images do
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
end