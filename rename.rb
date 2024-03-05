require 'fileutils'

def rename_files(directory)
  Dir.glob("#{directory}/**/*").each do |file|
    if File.file?(file) && File.extname(file) == '.jpeg'
      new_file = file.sub(/\.jpeg$/, '.jpg')
      FileUtils.mv(file, new_file)
    end
  end
end

# Replace 'your_directory' with the path to the directory you want to start from
rename_files('assets/images')