import { Card } from "@/components/ui/card";
import { Clock, Users, BarChart3, Shield, Store, FileText, CheckCircle, Zap, Lock, Menu, X, Home as HomeIcon, Sparkles, Lightbulb, Award, Mail } from "lucide-react";
import { ExpandableTabs } from "@/components/ui/expandable-tabs";
import { HeroGeometric } from "@/components/ui/hero-geometric";
import { InteractiveHoverButton } from "@/components/ui/interactive-hover-button";
import { APP_LOGO, APP_TITLE } from "@/const";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export default function Home() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [activeSection, setActiveSection] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
      
      // Calculate scroll progress
      const scrollTop = window.pageYOffset;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = Math.min(Math.max(scrollTop / docHeight, 0), 1);
      setScrollProgress(progress);
      
      // Determine active section with improved detection
      const sections = ['hero', 'features', 'how-it-works', 'benefits', 'contact'];
      const scrollPosition = window.scrollY + window.innerHeight / 3; // Use top third of viewport
      let newActiveSection = 0;
      
      // Find the section that's most visible
      sections.forEach((id, index) => {
        const element = document.getElementById(id);
        if (element) {
          const rect = element.getBoundingClientRect();
          const elementTop = rect.top + window.scrollY;
          const elementBottom = elementTop + rect.height;
          
          // Check if scroll position is within this section
          if (scrollPosition >= elementTop && scrollPosition < elementBottom) {
            newActiveSection = index;
          }
        }
      });
      
      setActiveSection(newActiveSection);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      const offset = 80; // Offset for fixed navigation
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth"
      });
    }
  };

  return (
    <div className="min-h-screen">

      {/* Scroll Progress Bar */}
      <div className="fixed top-0 left-0 w-full h-1 bg-gradient-to-r from-border/20 via-border/40 to-border/20 z-50">
        <div 
          className="h-full bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 transition-transform duration-150 ease-out"
          style={{ 
            transform: `scaleX(${scrollProgress})`,
            transformOrigin: 'left center',
          }}
        />
      </div>
      
      {/* Section Navigation Dots */}
      <div className="hidden lg:flex fixed right-8 top-1/2 -translate-y-1/2 z-40">
        <div className="space-y-4">
          {[
            { id: 'hero', label: 'Home' },
            { id: 'features', label: 'Features' },
            { id: 'how-it-works', label: 'How It Works' },
            { id: 'benefits', label: 'Benefits' },
            { id: 'contact', label: 'Contact' }
          ].map((section, index) => (
            <div key={section.id} className="relative group">
              <div className="absolute right-8 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap bg-background/95 backdrop-blur-md border border-border/60 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                {section.label}
              </div>
              <button
                onClick={() => scrollToSection(section.id)}
                className={`relative w-3 h-3 rounded-full border-2 transition-all duration-300 hover:scale-125 ${
                  activeSection === index 
                    ? 'bg-primary border-primary shadow-lg' 
                    : 'bg-transparent border-muted-foreground/40 hover:border-primary/60 hover:bg-primary/10'
                }`}
                aria-label={`Go to ${section.label}`}
              />
            </div>
          ))}
        </div>
      </div>
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-background/80 backdrop-blur-lg border-b border-border" : "bg-transparent"
      }`}>
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-8 h-8 text-primary" />
              <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Pramaan
              </span>
            </div>
            <div className="hidden md:flex items-center">
              <ExpandableTabs
                tabs={[
                  { title: "Home", icon: HomeIcon, onClick: () => scrollToSection("hero") },
                  { title: "Features", icon: Sparkles, onClick: () => scrollToSection("features") },
                  { title: "How It Works", icon: Lightbulb, onClick: () => scrollToSection("how-it-works") },
                  { title: "Benefits", icon: Award, onClick: () => scrollToSection("benefits") },
                  { type: "separator" },
                  { title: "Contact", icon: Mail, onClick: () => scrollToSection("contact") },
                ]}
                activeIndex={activeSection === 4 ? 5 : activeSection}
                activeColor="text-primary"
              />
            </div>
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
                className="md:hidden text-foreground"
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden mt-4 pb-4 space-y-3">
              <button 
                onClick={() => { scrollToSection("features"); setMobileMenuOpen(false); }} 
                className="block w-full text-left px-4 py-2 text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors"
              >
                Features
              </button>
              <button 
                onClick={() => { scrollToSection("how-it-works"); setMobileMenuOpen(false); }} 
                className="block w-full text-left px-4 py-2 text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors"
              >
                How It Works
              </button>
              <button 
                onClick={() => { scrollToSection("benefits"); setMobileMenuOpen(false); }} 
                className="block w-full text-left px-4 py-2 text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors"
              >
                Benefits
              </button>
              <button 
                onClick={() => { scrollToSection("contact"); setMobileMenuOpen(false); }} 
                className="block w-full text-left px-4 py-2 text-foreground/80 hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors"
              >
                Contact
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <section id="hero" className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
        <HeroGeometric 
          title1="Stop Time Theft."
          title2="Start Saving Thousands."
          description="Eliminate buddy punching and payroll fraud with AI-powered facial recognition. Track time with 99.9% accuracy across all locations—no cards, no codes, no cheating."
        />
        
        {/* CTA Buttons - Centered and aligned with content */}
        <div className="relative z-30 w-full container mx-auto px-4 md:px-6 -mt-8 md:-mt-12">
          <motion.div
            {...({
              initial: { opacity: 0, y: 20 },
              animate: { opacity: 1, y: 0 },
              transition: { duration: 1, delay: 1.2 }
            } as React.ComponentProps<typeof motion.div>)}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center max-w-7xl mx-auto lg:justify-start lg:pl-0"
          >
            <InteractiveHoverButton
              text="Get Started"
              type="button"
              onClick={(e) => {
                console.log("Get Started button clicked!");
                e.preventDefault();
                e.stopPropagation();
                // Force full page navigation - use replace to bypass React router completely
                console.log("Navigating to /login.html");
                window.location.replace("/login.html");
              }}
              className="text-white text-base font-semibold px-8 py-3.5 shadow-xl border-0 h-auto transition-all duration-300"
              style={{ backgroundColor: '#0d168f' }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#0a1157'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#0d168f'}
            />
          </motion.div>
        </div>

      </section>

      {/* Features Section */}
      <section id="features" className="py-24 bg-background">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Powerful Features
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Everything you need to manage your workforce efficiently and securely
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card className="p-8 hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 border-2 hover:border-primary/50 bg-card/50 backdrop-blur hover:bg-card/80 group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-6">
                <img src="/face-recognition.jpg" alt="Face Recognition" className="w-full h-full object-cover rounded-2xl" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-card-foreground">Facial Recognition</h3>
              <p className="text-muted-foreground leading-relaxed">
                Advanced AI-powered facial recognition ensures secure and accurate employee clock-in and clock-out, eliminating buddy punching and time theft.
              </p>
            </Card>

            <Card className="p-8 hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 border-2 hover:border-primary/50 bg-card/50 backdrop-blur hover:bg-card/80 group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-6">
                <img src="/multi-store.jpg" alt="Multi-Store" className="w-full h-full object-cover rounded-2xl" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-card-foreground">Multi-Store Management</h3>
              <p className="text-muted-foreground leading-relaxed">
                Manage multiple store locations from a single dashboard. Assign managers, track performance, and maintain oversight across your entire operation.
              </p>
            </Card>

            <Card className="p-8 hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 border-2 hover:border-primary/50 bg-card/50 backdrop-blur hover:bg-card/80 group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center mb-6">
                <BarChart3 className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-card-foreground">Detailed Reporting</h3>
              <p className="text-muted-foreground leading-relaxed">
                Comprehensive activity reports with Excel export capabilities. Track hours worked, earnings, attendance patterns, and employee performance metrics.
              </p>
            </Card>

            <Card className="p-8 hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 border-2 hover:border-primary/50 bg-card/50 backdrop-blur hover:bg-card/80 group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center mb-6">
                <FileText className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-card-foreground">Inventory Tracking</h3>
              <p className="text-muted-foreground leading-relaxed">
                Real-time inventory management with historical tracking. Submit snapshots, monitor stock levels, and maintain accurate records across all locations.
              </p>
            </Card>

            <Card className="p-8 hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 border-2 hover:border-primary/50 bg-card/50 backdrop-blur hover:bg-card/80 group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center mb-6">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-card-foreground">Role-Based Access</h3>
              <p className="text-muted-foreground leading-relaxed">
                Secure authentication with role-based permissions for stores, managers, and administrators. IP-based restrictions for enhanced security.
              </p>
            </Card>

            <Card className="p-8 hover:shadow-2xl transition-all duration-500 hover:-translate-y-3 border-2 hover:border-primary/50 bg-card/50 backdrop-blur hover:bg-card/80 group">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center mb-6">
                <img src="/analytics.jpg" alt="Analytics" className="w-full h-full object-cover rounded-2xl" />
              </div>
              <h3 className="text-2xl font-bold mb-3 text-card-foreground">End of Day Reports</h3>
              <p className="text-muted-foreground leading-relaxed">
                Streamlined EOD submission process for cash, credit, and sales totals. Track daily performance and maintain accurate financial records.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 bg-muted/30">
        
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              How It Works
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Simple three-step process to transform your workforce management
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <Card className="p-8 text-center bg-card border-2 hover:border-primary/50 transition-all duration-500 hover:shadow-2xl hover:-translate-y-2 group">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mx-auto mb-6 text-white text-3xl font-bold">
                1
              </div>
              <h3 className="text-2xl font-bold mb-4 text-card-foreground">Clock In with Face</h3>
              <p className="text-muted-foreground leading-relaxed">
                Employees use the time clock terminal to clock in and out using facial recognition. Fast, secure, and contactless authentication.
              </p>
            </Card>

            <Card className="p-8 text-center bg-card border-2 hover:border-primary/50 transition-all duration-500 hover:shadow-2xl hover:-translate-y-2 group">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mx-auto mb-6 text-white text-3xl font-bold">
                2
              </div>
              <h3 className="text-2xl font-bold mb-4 text-card-foreground">Real-Time Monitoring</h3>
              <p className="text-muted-foreground leading-relaxed">
                Managers monitor employee activities, attendance, and hours worked in real-time from their dashboard with live updates.
              </p>
            </Card>

            <Card className="p-8 text-center bg-card border-2 hover:border-primary/50 transition-all duration-500 hover:shadow-2xl hover:-translate-y-2 group">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center mx-auto mb-6 text-white text-3xl font-bold">
                3
              </div>
              <h3 className="text-2xl font-bold mb-4 text-card-foreground">Comprehensive Reports</h3>
              <p className="text-muted-foreground leading-relaxed">
                Administrators access detailed reports, analytics, and insights across all stores with powerful filtering and export capabilities.
              </p>
            </Card>
          </div>
        </div>

      </section>

      {/* Benefits Section */}
      <section id="benefits" className="py-24 bg-background">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Why Choose Pramaan
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Trusted by retail businesses for accurate time tracking and workforce management
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-12 max-w-5xl mx-auto">
            <div className="space-y-8">
              <div className="flex gap-4 p-6 rounded-xl bg-card border-2 border-transparent hover:border-primary/30 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <CheckCircle className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2 text-foreground group-hover:text-primary transition-colors duration-300">Eliminate Time Theft</h3>
                  <p className="text-muted-foreground">
                    Facial recognition prevents buddy punching and ensures only authorized employees can clock in, saving thousands in labor costs.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 p-6 rounded-xl bg-card border-2 border-transparent hover:border-primary/30 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Zap className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2 text-foreground group-hover:text-primary transition-colors duration-300">Save Time & Reduce Errors</h3>
                  <p className="text-muted-foreground">
                    Automated time tracking eliminates manual timesheets and reduces payroll processing time by up to 80%.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 p-6 rounded-xl bg-card border-2 border-transparent hover:border-primary/30 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Lock className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2 text-foreground group-hover:text-primary transition-colors duration-300">Enhanced Security</h3>
                  <p className="text-muted-foreground">
                    IP-based restrictions, encrypted data storage, and role-based access control ensure your sensitive information stays protected.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-8">
              <div className="flex gap-4 p-6 rounded-xl bg-card border-2 border-transparent hover:border-primary/30 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <BarChart3 className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2 text-foreground group-hover:text-primary transition-colors duration-300">Data-Driven Insights</h3>
                  <p className="text-muted-foreground">
                    Make informed decisions with comprehensive analytics on employee performance, attendance patterns, and labor costs.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 p-6 rounded-xl bg-card border-2 border-transparent hover:border-primary/30 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-500 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Store className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2 text-foreground group-hover:text-primary transition-colors duration-300">Scalable Solution</h3>
                  <p className="text-muted-foreground">
                    Easily manage one store or hundreds. Add new locations, employees, and managers as your business grows.
                  </p>
                </div>
              </div>

              <div className="flex gap-4 p-6 rounded-xl bg-card border-2 border-transparent hover:border-primary/30 hover:shadow-2xl hover:-translate-y-2 hover:scale-[1.02] transition-all duration-300 cursor-pointer group">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                    <Users className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2 text-foreground group-hover:text-primary transition-colors duration-300">Improved Accountability</h3>
                  <p className="text-muted-foreground">
                    Clear audit trails and detailed activity logs ensure transparency and accountability across your entire workforce.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-24 bg-background">  
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto text-center text-gray-600 md:px-8">
            <h3 className="text-gray-800 text-3xl font-semibold sm:text-4xl">
              Ready to Transform Your Workforce Management?
            </h3>
            <p className="mt-3 text-lg">
              Join businesses that trust Pramaan for secure, accurate, and efficient employee time tracking. Get started today with a personalized demo.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
               <InteractiveHoverButton
                 text="Get Started"
                 type="button"
                 onClick={(e) => {
                   console.log("Get Started button clicked!");
                   e.preventDefault();
                   e.stopPropagation();
                   // Force full page navigation - use replace to bypass React router completely
                   console.log("Navigating to /login.html");
                   window.location.replace("/login.html");
                 }}
                 className="text-white text-base font-semibold px-8 py-3.5 shadow-xl border-0 h-auto transition-all duration-300"
                 style={{ backgroundColor: '#0d168f' }}
                 onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#0a1157'}
                 onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#0d168f'}
               />
              <InteractiveHoverButton
                text="Learn More"
                onClick={() => scrollToSection("features")}
                className="border-2 text-base font-semibold px-8 py-3.5 h-auto transition-all duration-300"
                style={{ borderColor: '#0d168f', color: '#0d168f', backgroundColor: 'transparent' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#0d168f';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#0d168f';
                }}
              />
              <InteractiveHoverButton
                text="Contact Us"
                onClick={() => window.location.href = "/contact"}
                className="border-2 text-base font-semibold px-8 py-3.5 h-auto transition-all duration-300"
                style={{ borderColor: '#0d168f', color: '#0d168f', backgroundColor: 'transparent' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#0d168f';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = '#0d168f';
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-muted/30 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2">
              <Clock className="w-6 h-6 text-primary" />
              <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Pramaan
              </span>
            </div>
            <div className="flex gap-8 text-sm text-muted-foreground">
              <a href="#" className="hover:text-foreground transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-foreground transition-colors">Terms of Service</a>
              <a href="#" className="hover:text-foreground transition-colors">Support</a>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2024 Pramaan. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
