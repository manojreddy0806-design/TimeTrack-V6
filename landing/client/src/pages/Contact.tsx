import { InteractiveHoverButton } from "@/components/ui/interactive-hover-button";
import { motion } from "framer-motion";
import { Mail, Phone, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Contact() {
  const contactMethods = [
    {
      icon: <Mail className="w-6 h-6" />,
      contact: "Support@example.com"
    },
    {
      icon: <Phone className="w-6 h-6" />,
      contact: "+1 (555) 000-000"
    },
    {
      icon: <MapPin className="w-6 h-6" />,
      contact: "Mountain View, California, United State."
    },
  ];

  // ElegantShape component for background animation
  const ElegantShape = ({
    className,
    delay = 0,
    width = 400,
    height = 100,
    rotate = 0,
    gradient = "from-white/[0.08]",
  }: {
    className?: string;
    delay?: number;
    width?: number;
    height?: number;
    rotate?: number;
    gradient?: string;
  }) => {
    return (
      <motion.div
        initial={{
          opacity: 0,
          y: -150,
          rotate: rotate - 15,
        }}
        animate={{
          opacity: 1,
          y: 0,
          rotate: rotate,
        }}
        transition={{
          duration: 2.4,
          delay,
          ease: [0.23, 0.86, 0.39, 0.96],
          opacity: { duration: 1.2 },
        }}
        className={cn("absolute", className)}
      >
        <motion.div
          animate={{
            y: [0, 15, 0],
          }}
          transition={{
            duration: 12,
            repeat: Number.POSITIVE_INFINITY,
            ease: "easeInOut",
          }}
          style={{
            width,
            height,
          }}
          className="relative"
        >
          <div
            className={cn(
              "absolute inset-0 rounded-full",
              "bg-gradient-to-r to-transparent",
              gradient,
              "backdrop-blur-[2px] border-2 border-white/[0.15]",
              "shadow-[0_8px_32px_0_rgba(255,255,255,0.1)]",
              "after:absolute after:inset-0 after:rounded-full",
              "after:bg-gradient-to-r after:from-transparent after:to-white/[0.05]"
            )}
          />
        </motion.div>
      </motion.div>
    );
  };

  return (
    <main className="relative py-20 min-h-screen flex items-center overflow-hidden bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900">
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.05] via-transparent to-rose-500/[0.05] blur-3xl" />
      
      {/* Background image */}
      <div className="absolute inset-0 z-0">
        <img 
          src="/hero-bg.jpg" 
          alt="Background" 
          className="w-full h-full object-cover opacity-20"
        />
      </div>

      {/* Floating geometric shapes */}
      <div className="absolute inset-0 overflow-hidden z-[1]">
        <ElegantShape
          delay={0.3}
          width={600}
          height={140}
          rotate={12}
          gradient="from-indigo-500/[0.15]"
          className="left-[-10%] md:left-[-5%] top-[15%] md:top-[20%]"
        />

        <ElegantShape
          delay={0.5}
          width={500}
          height={120}
          rotate={-15}
          gradient="from-rose-500/[0.15]"
          className="right-[-5%] md:right-[0%] top-[70%] md:top-[75%]"
        />

        <ElegantShape
          delay={0.4}
          width={300}
          height={80}
          rotate={-8}
          gradient="from-violet-500/[0.15]"
          className="left-[5%] md:left-[10%] bottom-[5%] md:bottom-[10%]"
        />

        <ElegantShape
          delay={0.6}
          width={200}
          height={60}
          rotate={20}
          gradient="from-amber-500/[0.15]"
          className="right-[15%] md:right-[20%] top-[10%] md:top-[15%]"
        />

        <ElegantShape
          delay={0.7}
          width={150}
          height={40}
          rotate={-25}
          gradient="from-cyan-500/[0.15]"
          className="left-[20%] md:left-[25%] top-[5%] md:top-[10%]"
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 text-gray-600 md:px-8 w-full">
        <div className="max-w-6xl mx-auto gap-16 justify-center items-center lg:flex lg:max-w-none">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-lg mx-auto lg:mx-0 space-y-6"
          >
            <div className="text-center lg:text-left">
              <h3 className="text-indigo-400 font-semibold text-lg mb-2">
                Contact
              </h3>
              <p className="text-white text-3xl font-semibold sm:text-4xl mb-4">
                Let us know how we can help
              </p>
              <p className="text-gray-300 text-base leading-relaxed">
                We're here to help and answer any question you might have, We look forward to hearing from you! Please fill out the form, or us the contact information bellow .
              </p>
            </div>
            <div>
              <ul className="mt-8 flex flex-col gap-4">
                {contactMethods.map((item, idx) => (
                  <motion.li 
                    key={idx} 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: idx * 0.1 }}
                    className="flex items-center gap-x-4 p-5 rounded-xl bg-white/90 backdrop-blur-md border-2 border-white/30 hover:border-primary/50 hover:shadow-xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group"
                  >
                    <div className="flex-none text-gray-600 group-hover:text-primary transition-colors duration-300 group-hover:scale-110 w-10 h-10 flex items-center justify-center">
                      {item.icon}
                    </div>
                    <p className="group-hover:text-gray-900 transition-colors duration-300 text-sm sm:text-base text-gray-800 font-medium">{item.contact}</p>
                  </motion.li>
                ))}
              </ul>
            </div>
          </motion.div>
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex-1 mt-12 lg:mt-0 max-w-lg mx-auto lg:mx-0"
          >
            <form
              onSubmit={(e) => e.preventDefault()}
              className="space-y-6 p-8 rounded-2xl bg-white/95 backdrop-blur-md border-2 border-white/30 hover:border-primary/50 hover:shadow-2xl transition-all duration-300"
            >
              <div>
                <label className="font-medium text-gray-900 block mb-2">
                  Full name
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-4 py-3 text-gray-900 bg-white outline-none border-2 border-gray-300 focus:border-primary focus:ring-2 focus:ring-primary/30 focus:shadow-xl focus:-translate-y-1 focus:scale-[1.02] shadow-sm rounded-lg transition-all duration-300"
                />
              </div>
              <div>
                <label className="font-medium text-gray-900 block mb-2">
                  Email
                </label>
                <input
                  type="email"
                  required
                  className="w-full px-4 py-3 text-gray-900 bg-white outline-none border-2 border-gray-300 focus:border-primary focus:ring-2 focus:ring-primary/30 focus:shadow-xl focus:-translate-y-1 focus:scale-[1.02] shadow-sm rounded-lg transition-all duration-300"
                />
              </div>
              <div>
                <label className="font-medium text-gray-900 block mb-2">
                  Company
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-4 py-3 text-gray-900 bg-white outline-none border-2 border-gray-300 focus:border-primary focus:ring-2 focus:ring-primary/30 focus:shadow-xl focus:-translate-y-1 focus:scale-[1.02] shadow-sm rounded-lg transition-all duration-300"
                />
              </div>
              <div>
                <label className="font-medium text-gray-900 block mb-2">
                  Message
                </label>
                <textarea 
                  required 
                  className="w-full h-36 px-4 py-3 resize-none appearance-none bg-white text-gray-900 outline-none border-2 border-gray-300 focus:border-primary focus:ring-2 focus:ring-primary/30 focus:shadow-xl focus:-translate-y-1 focus:scale-[1.02] shadow-sm rounded-lg transition-all duration-300"
                ></textarea>
              </div>
              <InteractiveHoverButton
                text="Submit"
                type="submit"
                className="w-full text-white text-base font-semibold px-8 py-3.5 shadow-xl border-0 h-auto transition-all duration-300"
                style={{ backgroundColor: '#0d168f' }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#0a1157'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#0d168f'}
              />
            </form>
          </motion.div>
        </div>
      </div>
    </main>
  );
}

