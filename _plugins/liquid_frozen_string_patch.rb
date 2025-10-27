# Monkey patch Liquid to play nicely with Ruby's global frozen string literal flag.
require 'liquid'

module Liquid
  class Parser
    def argument
      str = +""
      if look(:id) && look(:colon, 1)
        str << consume
        str << consume
        str << ' '
      end

      str << expression
      str
    end
  end

  class For < Block
    def render_segment(context, segment)
      for_stack = context.registers[:for_stack] ||= []
      length = segment.length

      result = String.new

      context.stack do
        loop_vars = Liquid::ForloopDrop.new(@name, length, for_stack[-1])

        for_stack.push(loop_vars)

        begin
          context['forloop'.freeze] = loop_vars

          segment.each do |item|
            context[@variable_name] = item
            result << @for_block.render(context)
            loop_vars.send(:increment!)

            if context.interrupt?
              interrupt = context.pop_interrupt
              break if interrupt.is_a? BreakInterrupt
              next if interrupt.is_a? ContinueInterrupt
            end
          end
        ensure
          for_stack.pop
        end
      end

      result
    end
  end
end
